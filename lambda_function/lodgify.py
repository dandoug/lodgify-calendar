"""
Methods to call Lodgify API to get availability and rate data for a property and room
"""
import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from cachetools import cached

from caching import ResultsCache, cache_key
from helpers import build_error_response, date_from_str

# Global variable to hold the cached API key
_cached_api_key = None  # pylint: disable=invalid-name

# Global timeout value (seconds) used when calling Lodgify API.
TIMEOUT = 6

LODGIFY_API_BASE = 'https://api.lodgify.com'

# cache for saving results of calls to Lodgify API so that we call less often
CACHE_TTL_SECONDS = 300


# pylint: disable=too-many-arguments, too-many-positional-arguments
def get_availability(property_id, room_type_id, start_date, end_date, headers, origin):
    """ Get the availability data for the given property and room type."""
    availability = None
    error = None
    #  Get property availability
    date_query = f"start={start_date.isoformat()}&" + \
                 f"end={end_date.isoformat()}"
    url = (f"{LODGIFY_API_BASE}/v2/availability/{property_id}/{room_type_id}" +
           f"?includeDetails=true&{date_query}")
    try:
        response = requests.get(url, timeout=TIMEOUT, headers=headers)
        if response.status_code != 200:
            error = build_error_response(
                500,
                f"Error fetching availability: {response.status_code} {response.text}", origin)
        else:
            # find the availability that matches the room_type_id
            availability = None
            for room in response.json():
                if room['room_type_id'] == int(room_type_id):
                    availability = room
                    break
    except requests.exceptions.RequestException as e:
        error = build_error_response(500, f"Error fetching availability: {e}", origin)

    if not error and not availability:
        error = build_error_response(404, f"Room type {room_type_id} not found", origin)

    return availability, error


# pylint: disable=too-many-arguments, too-many-positional-arguments
def get_rates(property_id, room_type_id, start_date, end_date, headers, origin):
    """
    Get the rate data for the given property and room type.
    """
    rates = {}
    error = None
    # get rates
    try:
        date_query = f"StartDate={start_date.isoformat()}&" + \
                     f"EndDate={end_date.isoformat()}"
        url = (f"{LODGIFY_API_BASE}/v2/rates/calendar?RoomTypeId={room_type_id}" +
               f"&HouseId={property_id}&{date_query}")
        response = requests.get(url, timeout=TIMEOUT, headers=headers)
        if response.status_code != 200:
            error = build_error_response(
                500,
                f"Error fetching rates: {response.status_code} {response.text}", origin)
        else:
            rates = response.json()
    except requests.exceptions.RequestException as e:
        error = build_error_response(500, f"Error fetching availability: {e}", origin)

    return rates, error


# pylint: disable=too-many-locals
@cached(cache=ResultsCache(maxsize=1024, ttl=CACHE_TTL_SECONDS),
        key=cache_key, info=True)
def get_availability_and_rates(property_id, room_type_id, start_date, end_date, origin):
    """
    Get the availability and rates data for the given property and room type.
    """
    # Get the API key we need to build the headers used for both requests
    api_key, error = get_api_key(origin)
    if error:
        return None, None, error
    headers = {
            'X-ApiKey': api_key,
            'Accept': 'application/json'
        }

    # Call Lodgify to get availability and rates in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_availability = executor.submit(get_availability, property_id, room_type_id,
                                              start_date, end_date, headers, origin)
        future_rates = executor.submit(get_rates, property_id, room_type_id,
                                       start_date, end_date, headers, origin)
        # wait for the results
        try:
            # Wait for the results with a timeout
            availability, availability_error = future_availability.result(timeout=TIMEOUT)
            rates, rates_error = future_rates.result(timeout=TIMEOUT)
        except TimeoutError as e:
            # Handle timeout errors for the futures
            error = build_error_response(
                500, f"Request timed out while fetching availability or rates {e}", origin
            )
            return None, None, error

    # return the results and an error if there was one
    return availability, rates, availability_error if availability_error else rates_error


def get_api_key(origin):
    """
    Get the API key we need to call Lodgify
    """
    global _cached_api_key  # pylint: disable=global-statement
    if _cached_api_key is not None:
        # Return the cached API key if it's already fetched
        return _cached_api_key, None

    # Fetch the API key only once
    secret_service_url_base = os.environ.get('SECRET_SERVICE_BASE_URL')
    secret_name = os.environ.get('SECRET_NAME')
    url = f"{secret_service_url_base}/secretsmanager/get?secretId={secret_name}"
    headers = {"X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN')}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            error = build_error_response(
                500,
                f"Error fetching secret {secret_name}: " +
                f"{response.status_code} {response.text}", origin)
            return None, error
        # Cache the API key in memory
        # logging.debug("Secret received: %s", response.json())
        secret_json = json.loads(response.json()['SecretString'])
        _cached_api_key = secret_json['LODGIFY_API_KEY']
    except requests.exceptions.RequestException as e:
        error = build_error_response(500, f"Error fetching secret {secret_name}: {e}", origin)
        return None, error

    return _cached_api_key, None


def merge_calendar_availability_and_price_data(start_date, end_date, property_id,
                                               availability, rates, ):
    """
    Merge the availability and rate data into a response the front-end calendar can use
    """
    dates = {}
    return_data = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "propertyId": property_id,
        "room_type_id": availability.get('room_type_id', ''),
        "currency_code": rates.get('rate_settings', {}).get('currency_code', 'USD'),
        "dates": dates
    }
    # Build calendar data
    advanced_notice_days = rates.get('rate_settings', {}).get('advance_notice_days', 2)
    first_bookable_day = datetime.date.today() + datetime.timedelta(days=advanced_notice_days)
    # initialize the date map with empty entries
    date_range = (end_date - start_date).days + 1
    for i in range(date_range):
        current_date = start_date + datetime.timedelta(days=i)
        dates[current_date.isoformat()] = {}
    # process the periods and mark the entries as available or not available
    for period in availability.get('periods', []):
        period_available = period['available'] == 1
        period_date = date_from_str(period['start'])
        period_end = date_from_str(period['end'])
        while period_end >= period_date:
            if period_available and period_date >= first_bookable_day:
                dates[period_date.isoformat()]["available"] = True
            else:
                dates[period_date.isoformat()]["available"] = False
            period_date += datetime.timedelta(days=1)
    # for all the rates now, add them to their available day
    for cal in rates.get('calendar_items', []):
        if not cal.get('date'):
            continue  # skip any rates without a date
        rate_date = cal['date']
        if not dates[rate_date].get('available'):
            continue  # don't need rates in unavailable days
        prices = cal.get('prices', [])
        price = None
        if isinstance(prices, list) and len(prices) > 0:  # Check if prices is a valid list
            price = prices[0].get('price_per_day')  # fetch the first 'price_per_day'
        if price:
            dates[rate_date]['price'] = price
    return return_data
