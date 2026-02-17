import os
import requests
import json
try:
    # Try relative import first (when imported as module)
    from .utils import get_signature, get_headers, get_sydney_timestamps
except ImportError:
    # Fall back to absolute import (when run directly as script)
    from utils import get_signature, get_headers, get_sydney_timestamps

API_KEY = os.environ.get("API_KEY")
INVERTER_SN = os.environ.get("INVERTER_SN")
DOMAIN = "https://www.foxesscloud.com"
LANG = "en"

def get_real_query() -> dict:
    """Get the current working mode of the inverter."""
    try:
        path = "/op/v1/device/real/query"
        url = DOMAIN + path
        payload = {"sns": [INVERTER_SN], 
                    # "variables": ["meterPower", "SoC"]
                   }
        response = requests.post(url, json=payload, headers=get_headers(path, API_KEY), timeout=30)
        response.raise_for_status()  # Raise exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print("Network error while querying FoxESS API", e)
        raise
    except Exception as e:
        print("Unexpected error in get_real_query", e)
        raise

if __name__ == "__main__":
    data = get_real_query()
    print(json.dumps(data, indent=2))