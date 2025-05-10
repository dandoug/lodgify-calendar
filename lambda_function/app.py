"""
Call Lodgify API to get availability and rates for a given property and date range.
"""
import datetime
import json
import logging
import sys

from helpers import (setup_logging, check_origin, build_response, validate_query_parms,
                     date_from_str)
from lodgify import get_availability_and_rates

setup_logging()  # set logging levels


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

    origin = check_origin(event)

    # extract input from query params and validate
    end_date, start_date, property_id, room_type_id, error = validate_query_parms(event, origin)
    if error:
        return error

    # Call Lodgify to get availability and rates
    availability, rates, error = get_availability_and_rates(property_id, room_type_id,
                                                            start_date, end_date, origin)
    logging.warning(get_availability_and_rates.cache_info())  # put cache stats in the log
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
            price = prices[0].get('price_per_day')  # Access the first element and fetch 'price_per_day'
        if price:
            dates[rate_date]['price'] = price

    # Return JSON response
    return build_response(200, return_data, origin)


if __name__ == "__main__":
    """
    Script driver for local testing.
    Call with: python app.py <property_id> <room_type_id>
    
    requires secrets setup as described in tests/README.md and secrets_lambda_stub.py
    requires environment variables set as described in tests/README.md (maybe in a ide launcher)
    """
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
