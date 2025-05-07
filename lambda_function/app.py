import json
import datetime


def lambda_handler(event, context):
    # Parse query parameters for start and end dates
    query_params = event.get("queryStringParameters", {})

    # Get the current date
    today = datetime.date.today()

    # Default start date: first day of the current month
    start_date = datetime.datetime.strptime(
        query_params.get("startDate", today.replace(day=1).isoformat()),
        "%Y-%m-%d"
    ).date()

    # Default end date: two months after the start date
    end_date = datetime.datetime.strptime(
        query_params.get("endDate", (start_date + datetime.timedelta(days=60)).isoformat()),
        "%Y-%m-%d"
    ).date()

    date_range = (end_date - start_date).days + 1

    # Build calendar data
    dates = {}
    for i in range(date_range):
        current_date = start_date + datetime.timedelta(days=i)
        if i % 5 == 0:  # Simulate some unavailable dates
            dates[current_date.isoformat()] = {"available": False}
        else:
            dates[current_date.isoformat()] = {"available": True, "price": 100 + i * 5}

    # Return JSON response
    return {
        "statusCode": 200,
        "body": json.dumps({
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dates": dates
        }),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # Allow requests from any origin
        }
    }
