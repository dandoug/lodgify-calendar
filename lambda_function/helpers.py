"""
Utilities to support this lambda function.
"""
import datetime
import json
import logging
import os
from http.client import HTTPConnection
from typing import Any


def setup_logging():
    """
    Sets up the logging configuration for the application.

    This function configures the logging system to use the log level specified
    by the "LOGLEVEL" environment variable, defaulting to "WARN" if it is
    not set. It also enables debugging output for the `urllib3` library if
    the log level is set to "DEBUG" and sets the HTTP connection debug level
    accordingly.
    """
    # Optionally set log level from environment variable
    log_level = os.environ.get("LOGLEVEL", "WARN").upper()

    logging.basicConfig()
    logging.getLogger().setLevel(log_level)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)

    if log_level == "DEBUG":
        HTTPConnection.debuglevel = 1


def check_origin(_event):
    """
    It turns out that in production, the CORS check is done by the API gateway.  But
    when running locally, we need to be able to set '*'.  But we don't want to set
    that all the time because it gets double-set in production then.  So, we use an
    environment variable CORS_SPLAT, and if that is True, then we set the allowed origin to
    *.  If not, then we don't send the allowed origin header at all and let the gateway
    handle it.
    """
    cors_splat = os.getenv("CORS_SPLAT", "False").lower() == "true"
    if cors_splat:
        origin = "*"
    else:
        origin = None
    return origin


def build_error_response(status_code: int, message: str, origin="null") -> dict[str, Any]:
    """
    Build an error response
    """
    logging.error("%s: %s", status_code, message)
    return build_response(status_code, {"error": message}, origin=origin)


def build_response(status_code: int, body: dict[str, Any], origin=None) -> dict[str, Any]:
    """
    Build a response
    """
    headers = {
            "Content-Type": "application/json"
    }
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
    return {
        "statusCode": status_code,
        "body": json.dumps(body),
        "headers": headers
    }


def validate_query_parms(event, origin):
    """
    Validate the query parameters for the request.
    """
    query_params = event.get("queryStringParameters", {})
    error = None

    property_id = query_params.get("propertyId")
    if not property_id:
        error = build_error_response(400, "Missing propertyId query parameter", origin)

    room_type_id = query_params.get("roomTypeId")
    if not room_type_id:
        error = build_error_response(400, "Missing roomTypeId query parameter", origin)

    start_date = "#####"
    if not error:
        # Default start date: first day of the current month
        try:
            today = datetime.date.today()
            start_date = date_from_str(query_params.get("startDate",
                                                        today.replace(day=1).isoformat()))
        except ValueError as e:
            error = build_error_response(400,
                                         f"Invalid start date: {start_date} {e}", origin)
    # Default end date: two months after the start date
    end_date = "#####"
    if not error:
        try:
            end_date = date_from_str(
                query_params.get("endDate",
                                 (start_date + datetime.timedelta(days=60)).isoformat()))
        except ValueError as e:
            error = build_error_response(400,
                                         f"Invalid end date: {end_date} {e}", origin)
    # Validate date range
    if not error and end_date < start_date:
        error = build_error_response(400, "End date cannot be before start date", origin)
    # Check if the date range exceeds 6 months
    if not error and (end_date - start_date).days > 180:  # approximately 6 months
        error = build_error_response(400, "Date range cannot exceed 6 months", origin)

    return end_date, start_date, property_id, room_type_id, error


def date_from_str(date_str):
    """
    Create a Date object from a string in the format YYYY-MM-DD.
    """
    return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()


# pylint: disable=too-few-public-methods
class StubContext:
    """
    Stub context object for testing Lambda functions.
    """
    def __init__(self):
        self.function_name = "lambda_handler"
        self.function_version = "$LATEST"
        self.memory_limit_in_mb = 128
