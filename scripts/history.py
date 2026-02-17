"""
FoxESS History Data Utilities

This module provides functions for retrieving and processing historical data
from the FoxESS API, specifically for inverter monitoring and analysis.
"""


import hashlib
import time
import requests
import json
import csv
from datetime import datetime, timedelta
import pytz
import os
from rich import print
import re

# Use Streamlit secrets for sensitive config
import streamlit as st

# Handle imports for both direct execution and module import
try:
    # Try relative import first (when imported as module)
    from .utils import get_signature, get_headers, get_sydney_timestamps
except ImportError:
    # Fall back to absolute import (when run directly as script)
    from utils import get_signature, get_headers, get_sydney_timestamps


# API Configuration
DOMAIN = "https://www.foxesscloud.com"
LANG = "en"

# Load sensitive config from Streamlit secrets
API_KEY = st.secrets["API_KEY"]
INVERTER_SN = st.secrets["INVERTER_SN"]


def get_device_history_data(api_key: str, inverter_sn: str, variables: list = None,
                          ) -> dict:
    """
    Get device history data from FoxESS API.

    Args:
        api_key (str): FoxESS API key
        inverter_sn (str): Inverter serial number
        variables (list, optional): List of variables to query. Defaults to ['meterPower', 'SoC']
        start_time (str, optional): Start time in milliseconds for custom period
        end_time (str, optional): End time in milliseconds for custom period
        period (int, optional): Number of days to go back from today. Defaults to 1

    Returns:
        dict: API response containing historical data
    """
    if variables is None:
        variables = ['meterPower', 'SoC', 'batChargePower', 'batDischargePower']

    # Fetch 3 days of data from API (no period, no begin/end)
    path = '/op/v0/device/history/query'
    url = DOMAIN + path
    request_param = {
        'sn': inverter_sn,
        'variables': ['meterPower', 'SoC', 'batChargePower', 'batDischargePower']
    }

    try:
        print("Fetching FoxESS history data (3 days)...")
        response = requests.post(url, json=request_param, headers=get_headers(path, api_key), timeout=30)
        response.raise_for_status()
        api_response = response.json()

        # Transform the API response to our expected format
        transformed_result = []
        if 'result' in api_response and api_response['result']:
            timestamp_data = {}
            for variable_data in api_response['result']:
                if 'datas' in variable_data and variable_data['datas']:
                    for data_entry in variable_data['datas']:
                        variable_name = data_entry.get('name', 'Unknown')
                        unit = data_entry.get('unit', '')
                        if 'data' in data_entry and data_entry['data']:
                            for point in data_entry['data']:
                                timestamp = point.get('time', '')
                                value = point.get('value', '')
                                if timestamp not in timestamp_data:
                                    timestamp_data[timestamp] = {'time': timestamp, 'variables': {}}
                                timestamp_data[timestamp]['variables'][variable_name] = value
            transformed_result = list(timestamp_data.values())

        saved_files = []
        total_points = 0
        day_groups = {}
        for point in transformed_result:
            t = point.get('time')
            # print(t)
            if t:

                day_str = t[:10]  # Extract YYYY-MM-DD from timestamp string
                if day_str not in day_groups:
                    day_groups[day_str] = []
                day_groups[day_str].append(point)
                
        for day_str, points in day_groups.items():
            day_data = {
                'result': points,
                'success': True,
                'message': f'Retrieved {len(points)} data points for {day_str}'
            }
            day_str = re.sub(r'[:\-]', '', day_str)  # Remove colons and dashes for filename
            day_filename = f"history/foxess_history_{day_str}.csv"
            
            saved_file = save_history_data(day_data, day_filename)
            saved_files.append(saved_file)
            total_points += len(points)
            print(f"Saved {len(points)} data points to {saved_file}")

    except Exception as e:
        print(f"Error fetching history data: {e}")


def load_history_from_file(filename: str) -> dict:
    try:
        data_points = []
        with open(filename, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert CSV row back to API format
                data_point = {
                    'time': row.get('time', ''),
                    'variables': {}
                }
                
                # Add all columns except 'time' to variables
                for key, value in row.items():
                    if key != 'time':
                        # Try to convert numeric values
                        try:
                            # Check if it's a number
                            if '.' in str(value):
                                data_point['variables'][key] = float(value)
                            else:
                                data_point['variables'][key] = int(value)
                        except (ValueError, TypeError):
                            data_point['variables'][key] = value
                
                data_points.append(data_point)
        
    except FileNotFoundError:
        print(f"History file not found: {filename}")
        return {'result': [], 'success': False, 'message': f'File not found: {filename}'}
    except csv.Error as e:
        print(f"Invalid CSV in history file: {filename} - {e}")
        return {'result': [], 'success': False, 'message': f'Invalid CSV: {e}'}
    except Exception as e:
        print(f"Error reading history file: {filename} - {e}")
        return {'result': [], 'success': False, 'message': f'Error reading file: {e}'}


def save_history_data(data: dict, filename: str = None) -> str:
    """
    Save history data to a CSV file.

    Args:
        data (dict): History data to save
        filename (str, optional): Output filename. If None, generates based on current timestamp

    Returns:
        str: Path to the saved file
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"history/foxess_history_{timestamp}.csv"

    try:
        # Ensure the history directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Extract data points
        result_data = data.get('result', [])
        
        if not result_data:
            print("No data points to save")
            return filename


        # Determine all variable names across all data points
        variable_names = set()
        for point in result_data:
            if 'variables' in point and isinstance(point['variables'], dict):
                variable_names.update(point['variables'].keys())
        # If no variables found, fallback to default
        if not variable_names:
            variable_names = set(['meterPower', 'SoC', 'batChargePower', 'batDischargePower'])
        columns = ['time'] + sorted(variable_names)

        # Write to CSV
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for point in result_data:
                row = {'time': point.get('time', '')}
                # Add all variable columns, fill with value or empty if missing
                for var_name in columns[1:]:
                    if 'variables' in point and isinstance(point['variables'], dict):
                        row[var_name] = point['variables'].get(var_name, '')
                    else:
                        row[var_name] = ''
                writer.writerow(row)

        total_points = len(result_data)
        print(f"History data saved to {filename}")
        print(f"Total data points: {total_points}")

        return filename

    except Exception as e:
        print(f"Error saving history data: {e}")
        raise


if __name__ == "__main__":
    # Example usage: Fetch and save 1 day of history data (will create 1 file)
    try:
        print("Fetching FoxESS history data...")

        # Fetch 1 day    of history data (will save each day to separate files)
        history_data = get_device_history_data(
            api_key=API_KEY,
            inverter_sn=INVERTER_SN,
            variables=["MeterPower", "SoC", "BatChargePower", "BatDischargePower"]
        )

    except Exception as e:
        print(f"Error in history collection: {e}")
