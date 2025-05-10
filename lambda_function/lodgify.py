"""
Methods to call Lodgify API to get availability and rate data for a property and room
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from cachetools import cached

from caching import ResultsCache, cache_key
from helpers import build_error_response

# Global variable to hold the cached API key
_cached_api_key = None

# Global timeout value (seconds) used when calling Lodgify API.
TIMEOUT = 6

LODGIFY_API_BASE = 'https://api.lodgify.com'

# cache for saving results of calls to Lodgify API so that we call less often
CACHE_TTL_SECONDS = 300


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
    global _cached_api_key  # Use the global variable
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
                f"Error fetching secret {secret_name}: {response.status_code} {response.text}", origin)
            return None, error
        # Cache the API key in memory
        # logging.debug("Secret received: %s", response.json())
        secret_json = json.loads(response.json()['SecretString'])
        _cached_api_key = secret_json['LODGIFY_API_KEY']
    except requests.exceptions.RequestException as e:
        error = build_error_response(500, f"Error fetching secret {secret_name}: {e}", origin)
        return None, error

    return _cached_api_key, None
