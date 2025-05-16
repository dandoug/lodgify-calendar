from helpers import date_from_str
import pytest


def test_date_from_str():
    # Test regular date
    date = date_from_str("2025-05-14")
    assert date.year == 2025
    assert date.month == 5
    assert date.day == 14

    # Test end of year date
    date = date_from_str("2025-12-31")
    assert date.year == 2025
    assert date.month == 12
    assert date.day == 31

    # Test leap year date
    date = date_from_str("2024-02-29")
    assert date.year == 2024
    assert date.month == 2
    assert date.day == 29

    # Test invalid cases
    with pytest.raises(ValueError):
        date_from_str("2025/05/14")  # Wrong format

    with pytest.raises(ValueError):
        date_from_str("2025-13-01")  # Invalid month

    with pytest.raises(ValueError):
        date_from_str("2025-04-31")  # Invalid day
