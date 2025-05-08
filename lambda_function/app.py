"""
Call Lodgify API to get availability and rates for a given property and date range.
"""
import datetime
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests

TIMEOUT = 6

LODGIFY_API_BASE = 'https://api.lodgify.com'

# Global variable to hold the cached API key
_cached_api_key = None

# Optionally set log level from environment variable
log_level = os.environ.get("LOGLEVEL", "WARN").upper()

logging.basicConfig()
logging.getLogger().setLevel(log_level)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

from http.client import HTTPConnection

if log_level == "DEBUG":
    HTTPConnection.debuglevel = 1


# pylint: disable=too-many-locals
def lambda_handler(event, _context):
    """
    Handles an AWS Lambda function to fetch and process availability and rate data
    for a given property and date range by interacting with Lodgify's API. The function
    validates the input parameters, retrieves data from Lodgify, processes it to
    determine availability and rates for a specific property, and returns the
    information in a structured JSON format.

    Parameters:
        event (dict): AWS Lambda event object containing HTTP request details such
            as query parameters.
        _context (Any): AWS Lambda context object providing runtime information.

    Returns:
        dict: A JSON-compatible dictionary representing availability and rate
            information for the given property and dates.
    """

    # Check origin
    origin, error = _check_origin(event)
    if error:
        return error

    # extract input from query params and validate
    end_date, start_date, property_id, room_type_id, error = _validate_query_parms(event, origin)
    if error:
        return error

    # Call Lodgify to get availability and rates
    availability, rates, error = _get_availability_and_rates(property_id, room_type_id,
                                                             start_date, end_date, origin)
    if error:
        return error

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
        period_date = _date_from_str(period['start'])
        period_end = _date_from_str(period['end'])
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
            price = prices[0].get('price_per_day')  # Access the first element and fetch 'price_per_day'
        if price:
            dates[rate_date]['price'] = price

    # Return JSON response
    return _build_response(200, return_data, origin)


def _is_origin_allowed(origin: str, cors_whitelist: str) -> bool:
    if cors_whitelist == "*":
        return True
    if not origin:
        return False
    allowed_origins = cors_whitelist.split(",")
    return origin.lower() in allowed_origins


def _check_origin(event):
    cors_whitelist = os.getenv("CORS_WHITELIST", "*")
    origin = event.get("headers", {}).get("Origin", "*")
    error = None
    if not _is_origin_allowed(origin, cors_whitelist):
        error = _build_error_response(403, f"Origin not allowed, {origin}", "null")
    if cors_whitelist == "*":
        origin = "*"
    return origin, error


def _get_availability(property_id, room_type_id, start_date, end_date, headers, origin):

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
            error = _build_error_response(
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
        error = _build_error_response(500, f"Error fetching availability: {e}", origin)

    if not error and not availability:
        error = _build_error_response(404, f"Room type {room_type_id} not found", origin)

    return availability, error


def _get_rates(property_id, room_type_id, start_date, end_date, headers, origin):

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
            error = _build_error_response(
                500,
                f"Error fetching rates: {response.status_code} {response.text}", origin)
        else:
            rates = response.json()
    except requests.exceptions.RequestException as e:
        error = _build_error_response(500, f"Error fetching availability: {e}", origin)

    return rates, error


def _get_availability_and_rates(property_id, room_type_id, start_date, end_date, origin):
    # Get the API key we need to build the headers used for both requests
    api_key, error = _get_api_key(origin)
    if error:
        return None, None, error
    headers = {
            'X-ApiKey': api_key,
            'Accept': 'application/json'
        }

    # Call Lodgify to get availability and rates in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_availability = executor.submit(_get_availability, property_id, room_type_id,
                                              start_date, end_date, headers, origin)
        future_rates = executor.submit(_get_rates, property_id, room_type_id,
                                       start_date, end_date, headers, origin)
        # wait for the results
        try:
            # Wait for the results with a timeout
            availability, availability_error = future_availability.result(timeout=TIMEOUT)
            rates, rates_error = future_rates.result(timeout=TIMEOUT)
        except TimeoutError as e:
            # Handle timeout errors for the futures
            error = _build_error_response(
                500, f"Request timed out while fetching availability or rates {e}", origin
            )
            return None, None, error


    # return the results and an error if there was one
    return availability, rates, availability_error if availability_error else rates_error


def _build_error_response(status_code: int, message: str, origin="null") -> dict[str, Any]:
    logging.error("%s: %s", status_code, message)
    return _build_response(status_code, {"error": message}, origin=origin)


def _build_response(status_code: int, body: dict[str, Any], origin="null") -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": f"{origin}"
        }
    }


def _get_api_key(origin):
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
            error = _build_error_response(
                500,
                f"Error fetching secret {secret_name}: {response.status_code} {response.text}", origin)
            return None, error
        # Cache the API key in memory
        # logging.debug("Secret received: %s", response.json())
        secret_json = json.loads(response.json()['SecretString'])
        _cached_api_key = secret_json['LODGIFY_API_KEY']
    except requests.exceptions.RequestException as e:
        error = _build_error_response(500, f"Error fetching secret {secret_name}: {e}", origin)
        return None, error

    return _cached_api_key, None


def _validate_query_parms(event, origin):
    # Parse query parameters for start and end dates
    query_params = event.get("queryStringParameters", {})
    error = None

    property_id = query_params.get("propertyId")
    if not property_id:
        error = _build_error_response(400, "Missing propertyId query parameter", origin)

    room_type_id = query_params.get("roomTypeId")
    if not room_type_id:
        error = _build_error_response(400, "Missing roomTypeId query parameter", origin)

    start_date = "#####"
    if not error:
        # Default start date: first day of the current month
        try:
            today = datetime.date.today()
            start_date = _date_from_str(query_params.get("startDate",
                                                         today.replace(day=1).isoformat()))
        except ValueError as e:
            error = _build_error_response(400,
                                          f"Invalid start date: {start_date} {e}", origin)
    # Default end date: two months after the start date
    end_date = "#####"
    if not error:
        try:
            end_date = _date_from_str(
                query_params.get("endDate",
                                 (start_date + datetime.timedelta(days=60)).isoformat()))
        except ValueError as e:
            error = _build_error_response(400,
                                          f"Invalid end date: {end_date} {e}", origin)
    # Validate date range
    if not error and end_date < start_date:
        error = _build_error_response(400, "End date cannot be before start date", origin)
    # Check if the date range exceeds 6 months
    if not error and (end_date - start_date).days > 180:  # approximately 6 months
        error = _build_error_response(400, "Date range cannot exceed 6 months", origin)

    return end_date, start_date, property_id, room_type_id, error


def _date_from_str(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()


if __name__ == "__main__":
    _property_id = sys.argv[1]
    _room_type_id = sys.argv[2]

    # Create a sample event
    test_event = {
        "queryStringParameters": {
            "propertyId": _property_id,
            "roomTypeId": _room_type_id,
            "startDate": "2025-05-01",
            "endDate": "2025-06-30"
        }
    }

    # pylint: disable=too-few-public-methods
    class _StubContext:
        """
        Stub context object for testing Lambda functions.
        """
        def __init__(self):
            self.function_name = "lambda_handler"
            self.function_version = "$LATEST"
            self.memory_limit_in_mb = 128


    # Call the handle
    result = lambda_handler(test_event, _StubContext())
    print(json.dumps(result, indent=2))
