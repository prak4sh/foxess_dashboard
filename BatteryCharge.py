import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import glob
import os

def display_battery_charge():
    st.text("🔋 Battery Charge & Discharge Power (Hourly Average)")
    history_folder = "history"
    csv_files = glob.glob(os.path.join(history_folder, "foxess_history_*.csv"))
    if not csv_files:
        st.warning("No battery history data found. Please run the history collection script first.")
        return
    all_data = []
    for csv_file in sorted(csv_files):
        try:
            df = pd.read_csv(csv_file)
            if not df.empty and 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'], errors='coerce', utc=True)
                df['time'] = df['time'].dt.tz_convert('Australia/Sydney')
                all_data.append(df)
        except Exception as e:
            st.warning(f"Error reading {csv_file}: {e}")
            continue
    if not all_data:
        st.error("No valid battery data found in CSV files.")
        return
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values('time').dropna(subset=['time'])
    if combined_df.empty:
        st.error("No valid data after processing.")
        return

    # Find charge/discharge columns
    charge_col = None
    discharge_col = None
    for c in ["Charge Power", "batChargePower"]:
        if c in combined_df.columns:
            charge_col = c
            break
    for c in ["Discharge Power", "batDischargePower"]:
        if c in combined_df.columns:
            discharge_col = c
            break
    if charge_col and discharge_col:
        hourly_df = combined_df.set_index('time')
        hourly_avg = hourly_df[[charge_col, discharge_col]].resample('1h').mean().reset_index()
        fig_power = go.Figure()
        fig_power.add_trace(go.Scatter(
            x=hourly_avg['time'],
            y=hourly_avg[charge_col],
            mode='lines',
            name='Charge Power (Hourly Avg)',
            line=dict(color='#00C9A7', width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(0, 201, 167, 0.15)'
        ))
        fig_power.add_trace(go.Scatter(
            x=hourly_avg['time'],
            y=hourly_avg[discharge_col],
            mode='lines',
            name='Discharge Power (Hourly Avg)',
            line=dict(color='#FF6F61', width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(255, 111, 97, 0.15)'
        ))
        fig_power.update_layout(
            # title="Battery Charge & Discharge Power (Hourly Average)",
            xaxis_title="Time (Hourly)",
            yaxis_title="Power (kW)",
            height=500,
            showlegend=True,
            hovermode='x unified',
            font=dict(family="Segoe UI, Arial", size=14)
        )
        # fig_power.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5')
        min_y = min(hourly_avg[charge_col].min(), hourly_avg[discharge_col].min(), 0)
        max_y = max(hourly_avg[charge_col].max(), hourly_avg[discharge_col].max(), 1)
        # fig_power.update_yaxes(range=[min_y - 0.1, max_y + 0.1], showgrid=True, gridwidth=1, gridcolor='#e5e5e5', zeroline=True, zerolinecolor='#888')
        st.plotly_chart(fig_power, width='stretch')
    else:
        st.info("Charge/Discharge power data not available in the selected files.")
