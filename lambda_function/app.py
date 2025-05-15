"""
Call Lodgify API to get availability and rates for a given property and date range.
"""
import json
import logging
import sys

from helpers import setup_logging, check_origin, build_response, validate_query_parms
from lodgify import get_availability_and_rates, merge_calendar_availability_and_price_data

setup_logging()  # set logging levels


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

    return_data = merge_calendar_availability_and_price_data(start_date, end_date,
                                                             property_id, availability, rates)

    # Return JSON response
    return build_response(200, return_data, origin)


if __name__ == "__main__":
    # Script driver for local testing.
    # Call with: python app.py <property_id> <room_type_id>
    #
    # requires secrets setup as described in tests/README.md and secrets_lambda_stub.py
    # requires environment variables set as described in tests/README.md (maybe in a ide launcher)
    # pylint: disable=ungrouped-imports
    from helpers import StubContext

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

    # Call the handle
    result = lambda_handler(test_event, StubContext())
    print(json.dumps(result, indent=2))
