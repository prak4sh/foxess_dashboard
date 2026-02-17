"""
FoxESS Utility Functions

This module provides common utility functions for FoxESS API interactions,
including authentication, timestamp generation, and header creation.
"""

import hashlib
import time
from datetime import datetime, timedelta
import pytz

# API Configuration
DOMAIN = "https://www.foxesscloud.com"
LANG = "en"


def get_signature(path: str, token: str) -> tuple[str, str]:
    """
    Generate API signature for authentication.

    Args:
        path (str): API endpoint path
        token (str): API authentication token

    Returns:
        tuple: (signature, timestamp)
    """
    timestamp = str(int(time.time() * 1000))
    url = DOMAIN + path
    signature_string = fr"{path}\r\n{token}\r\n{timestamp}"
    signature = hashlib.md5(signature_string.encode()).hexdigest()
    return signature, timestamp


def get_headers(path: str, token: str) -> dict:
    """
    Generate request headers with authentication.

    Args:
        path (str): API endpoint path
        token (str): API authentication token

    Returns:
        dict: Request headers
    """
    signature, timestamp = get_signature(path, token)
    return {
        "Content-Type": "application/json",
        "token": token,
        "timestamp": timestamp,
        "signature": signature,
        "lang": LANG,
        "User-Agent": "python-requests/2.0 (FoxESS API Client)"
    }


def get_sydney_timestamps(hours: list = None) -> dict:
    """
    Generate timestamps for Sydney timezone at specified hours.

    Args:
        hours (list, optional): List of hours to generate timestamps for.
                               Defaults to [17, 19] for yesterday.

    Returns:
        dict: Dictionary mapping "HH:00" to timestamp_ms
    """
    if hours is None:
        hours = [17, 19]

    sydney_tz = pytz.timezone('Australia/Sydney')
    today = datetime.now(sydney_tz).date()
    yesterday = today - timedelta(days=1)
    timestamps = {}

    for hour in hours:
        dt = sydney_tz.localize(datetime.combine(yesterday, datetime.min.time().replace(hour=hour)))
        timestamp_ms = int(dt.timestamp() * 1000)
        timestamps[f"{hour:02d}:00"] = timestamp_ms

    return timestamps


if __name__ == "__main__":
    # Example usage
    print("Testing utility functions...")

    # Test get_sydney_timestamps
    timestamps = get_sydney_timestamps([17, 19])
    print(f"Sydney timestamps: {timestamps}")

    # Test get_signature (with dummy token)
    signature, timestamp = get_signature("/test/path", "dummy_token")
    print(f"Signature: {signature}")
    print(f"Timestamp: {timestamp}")

    # Test get_headers (with dummy token)
    headers = get_headers("/test/path", "dummy_token")
    print(f"Headers keys: {list(headers.keys())}")