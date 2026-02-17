"""
FoxESS Dashboard Application

This Streamlit application provides a web-based dashboard for monitoring and managing
the FoxESS solar inverter system. It includes authentication, real-time data visualization,
and settings management.

Features:
- User authentication with secure login/logout
- Sidebar navigation with Home and Settings pages
- Real-time display of inverter status and historical data
- Configuration management for system parameters

Dependencies:
- streamlit: Web app framework
- streamlit_option_menu: Enhanced sidebar menu
- streamlit_authenticator: Authentication component
- PyYAML: YAML configuration file handling
"""


import streamlit as st
import subprocess
import json
from home import display_home
import yaml
import streamlit_authenticator as stauth

import pandas as pd
from streamlit_option_menu import option_menu

import glob
import os
import plotly.graph_objects as go
# Import battery page modules
from BatteryPercentage import display_battery_percentage
from BatteryCharge import display_battery_charge
from BatterySummary import display_battery_summary
from MeterPower import display_meter_power
from TotalPowerExport import display_total_power_export



# Recursively convert all nested secrets to standard dicts
def to_dict(obj):
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif hasattr(obj, 'items'):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_dict(i) for i in obj]
    else:
        return obj

credentials = to_dict(st.secrets["credentials"])

cookie_key = st.secrets["cookie_key"]
cookie_name = st.secrets.get("cookie_name", "foxess_dashboard_cookie")
expiry_days = int(st.secrets.get("expiry_days", 30))

authenticator = stauth.Authenticate(
    credentials,
    cookie_name,
    cookie_key,
    expiry_days
)

# Attempt user login
try:
    authenticator.login()
except Exception as e:
    st.error(e)

def display_battery_dashboard():
    """
    Display the battery dashboard with SoC charts and statistics.
    """
    try:
        # Get all CSV files from history folder
        history_folder = "history"
        csv_files = glob.glob(os.path.join(history_folder, "foxess_history_*.csv"))

        if not csv_files:
            st.warning("No battery history data found. Please run the history collection script first.")
            return

        # Load and combine all CSV files
        all_data = []
        for csv_file in sorted(csv_files):
            try:
                df = pd.read_csv(csv_file)
                if not df.empty and 'time' in df.columns and 'SoC' in df.columns:
                    # Convert time column to datetime, handling timezones properly
                    df['time'] = pd.to_datetime(df['time'], errors='coerce', utc=True)
                    # Convert to local timezone for consistency
                    df['time'] = df['time'].dt.tz_convert('Australia/Sydney')
                    # Add date column for grouping (tz-naive for comparison)
                    df['date'] = df['time'].dt.date
                    all_data.append(df)
            except Exception as e:
                st.warning(f"Error reading {csv_file}: {e}")
                continue

        if not all_data:
            st.error("No valid battery data found in CSV files.")
            return

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.sort_values('time').dropna(subset=['time', 'SoC'])

        if combined_df.empty:
            st.error("No valid data after processing.")
            return

        # Display summary statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Current SoC", f"{combined_df['SoC'].iloc[-1]:.1f}%")
        with col2:
            st.metric("Average SoC", f"{combined_df['SoC'].mean():.1f}%")
        with col3:
            st.metric("Min SoC", f"{combined_df['SoC'].min():.1f}%")
        with col4:
            st.metric("Max SoC", f"{combined_df['SoC'].max():.1f}%")

        # Date range selector
        st.subheader("📊 Battery State of Charge Over Time")

        # Get date range - ensure we work with date objects only
        min_date = combined_df['date'].min()
        max_date = combined_df['date'].max()

        # Allow some flexibility in date selection (go back 30 days from min, forward 30 days from max)
        flexible_min = min_date - pd.Timedelta(days=30)
        flexible_max = max_date + pd.Timedelta(days=30)

        # Set reasonable default date range (last 3 days of data)
        default_start = max(min_date, max_date - pd.Timedelta(days=3))
        default_end = max_date

        col1, col2, col3 = st.columns([1, 1, 1.2])
        with col1:
            start_date = st.date_input("Start Date", default_start, min_value=flexible_min, max_value=flexible_max, key="battery_start_date")
        with col2:
            end_date = st.date_input("End Date", default_end, min_value=flexible_min, max_value=flexible_max, key="battery_end_date")
        with col3:
            graph_option = st.selectbox(
                "Show graph for:",
                ["Battery Percentage", "Charge Power"],
                key="battery_graph_option"
            )

        # Filter data by date range - ensure we're comparing date objects
        mask = (combined_df['date'] >= start_date) & (combined_df['date'] <= end_date)
        filtered_df = combined_df[mask].copy()  # Make a copy to avoid issues

        # Show current selection info
        st.info(f"📅 Showing data from {start_date} to {end_date} ({len(filtered_df)} data points)")

        if filtered_df.empty:
            st.warning(f"No data available for the selected date range ({start_date} to {end_date}).")
            st.info("Try selecting a date range that includes your available data.")
            # Show data availability info
            st.subheader("📊 Data Availability")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Available Data From", str(min_date))
            with col2:
                st.metric("Available Data To", str(max_date))
            return

        if graph_option == "Battery Percentage":
            # --- Battery SoC Graph ---
            st.subheader("📊 Battery State of Charge Over Time")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=filtered_df['time'],
                y=filtered_df['SoC'],
                mode='lines',
                name='Battery SoC',
                line=dict(color='#2E86AB', width=2),
                fill='tozeroy',
                fillcolor='rgba(46, 134, 171, 0.1)'
            ))
            fig.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="100% (Full)")
            fig.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="20% (Low)")
            fig.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="80% (High)")
            fig.update_layout(
                title="Battery State of Charge (SoC) Over Time",
                xaxis_title="Time",
                yaxis_title="State of Charge (%)",
                height=500,
                showlegend=True,
                hovermode='x unified',
                font=dict(family="Segoe UI, Arial", size=14)
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5')
            fig.update_yaxes(range=[0, 110], showgrid=True, gridwidth=1, gridcolor='#e5e5e5', zeroline=True, zerolinecolor='#888')
            st.plotly_chart(fig, width='stretch')
        else:
            # --- Battery Charge/Discharge Power Graph (Hourly Averaged) ---
            st.subheader("🔋 Battery Charge & Discharge Power (Hourly Average)")
            charge_col = None
            discharge_col = None
            for c in ["Charge Power", "batChargePower"]:
                if c in filtered_df.columns:
                    charge_col = c
                    break
            for c in ["Discharge Power", "batDischargePower"]:
                if c in filtered_df.columns:
                    discharge_col = c
                    break
            if charge_col and discharge_col:
                # Set time as index for resampling
                hourly_df = filtered_df.set_index('time')
                # Resample to 1 hour, taking the mean for each hour (use '1h' instead of deprecated '1H')
                hourly_avg = hourly_df[[charge_col, discharge_col]].resample('1h').mean().reset_index()
                fig_power = go.Figure()
                fig_power.add_trace(go.Scatter(
                    x=hourly_avg['time'],
                    y=hourly_avg[charge_col],
                    mode='lines+markers',
                    name='Charge Power (Hourly Avg)',
                    line=dict(color='#00C9A7', width=2),
                    marker=dict(size=6),
                    fill='tozeroy',
                    fillcolor='rgba(0, 201, 167, 0.15)'
                ))
                fig_power.add_trace(go.Scatter(
                    x=hourly_avg['time'],
                    y=hourly_avg[discharge_col],
                    mode='lines+markers',
                    name='Discharge Power (Hourly Avg)',
                    line=dict(color='#FF6F61', width=2),
                    marker=dict(size=6),
                    fill='tozeroy',
                    fillcolor='rgba(255, 111, 97, 0.15)'
                ))
                fig_power.update_layout(
                    title="Battery Charge & Discharge Power (Hourly Average)",
                    xaxis_title="Time (Hourly)",
                    yaxis_title="Power (kW)",
                    height=500,
                    showlegend=True,
                    hovermode='x unified',
                    font=dict(family="Segoe UI, Arial", size=14)
                )
                fig_power.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5')
                min_y = min(hourly_avg[charge_col].min(), hourly_avg[discharge_col].min(), 0)
                max_y = max(hourly_avg[charge_col].max(), hourly_avg[discharge_col].max(), 1)
                fig_power.update_yaxes(range=[min_y - 0.1, max_y + 0.1], showgrid=True, gridwidth=1, gridcolor='#e5e5e5', zeroline=True, zerolinecolor='#888')
                st.plotly_chart(fig_power, width='stretch')
            else:
                st.info("Charge/Discharge power data not available in the selected files.")

        # Daily summary chart
        st.subheader("📈 Daily SoC Summary")

        # Group by date and calculate daily statistics
        daily_stats = filtered_df.groupby('date')['SoC'].agg(['mean', 'min', 'max']).reset_index()

        # Create daily summary chart
        fig2 = go.Figure()

        # Add daily average
        fig2.add_trace(go.Scatter(
            x=daily_stats['date'],
            y=daily_stats['mean'],
            mode='lines+markers',
            name='Daily Average',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=8)
        ))

        # Add min/max range
        fig2.add_trace(go.Scatter(
            x=daily_stats['date'],
            y=daily_stats['max'],
            mode='lines',
            name='Daily Max',
            line=dict(color='lightgreen', width=1, dash='dot'),
            showlegend=True
        ))

        fig2.add_trace(go.Scatter(
            x=daily_stats['date'],
            y=daily_stats['min'],
            mode='lines',
            name='Daily Min',
            line=dict(color='lightcoral', width=1, dash='dot'),
            fill='tonexty',
            fillcolor='rgba(255, 0, 0, 0.1)',
            showlegend=True
        ))

        fig2.update_layout(
            title="Daily Battery SoC Statistics",
            xaxis_title="Date",
            yaxis_title="State of Charge (%)",
            height=400,
            hovermode='x unified'
        )

        fig2.update_yaxes(range=[0, 110])

        st.plotly_chart(fig2, width='stretch')


    except Exception as e:
        st.error(f"Error loading battery data: {e}")
        st.info("Make sure the history folder contains valid CSV files with 'time' and 'SoC' columns.")



if st.session_state.get("authentication_status"):
    # Sidebar configuration with menu options - only show when authenticated
    with st.sidebar:
        selected = option_menu(
            "Main Menu",
            ["Home", "Battery Percentage", "Battery Charge", "Battery Summary", "Meter Power", "Total Power Export", "Settings"],
            icons=["house", "percent", "battery", "bar-chart", "plug", "upload", "gear"],
            menu_icon="cast",
            default_index=0,
            key="menu_selection"
        )
        # Logout button using authenticator's built-in logout
        authenticator.logout("Logout", "sidebar")
    # Render content based on selected menu option
    if selected == "Home":
        display_home()
    elif selected == "Battery Percentage":
        display_battery_percentage()
    elif selected == "Battery Charge":
        display_battery_charge()
    elif selected == "Battery Summary":
        display_battery_summary()
    elif selected == "Meter Power":
        display_meter_power()
    elif selected == "Total Power Export":
        display_total_power_export()


    if selected == "Settings":
        st.header("Settings")
        st.write("Configure system parameters, thresholds, and preferences.")
        # TODO: Add settings page content - forms for updating config.yaml or main.py parameters

# If not authenticated, the login form will be displayed automatically by authenticator.login()
