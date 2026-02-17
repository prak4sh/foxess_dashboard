import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import glob
import os

def display_meter_power():
    # st.header("⚡ Meter Power")
    history_folder = "history"
    csv_files = glob.glob(os.path.join(history_folder, "foxess_history_*.csv"))
    if not csv_files:
        st.warning("No meter power data found. Please run the history collection script first.")
        return
    all_data = []
    for csv_file in sorted(csv_files):
        try:
            df = pd.read_csv(csv_file)
            if not df.empty and 'time' in df.columns and 'MeterPower' in df.columns:
                df['time'] = pd.to_datetime(df['time'], errors='coerce', utc=True)
                df['time'] = df['time'].dt.tz_convert('Australia/Sydney')
                all_data.append(df)
        except Exception as e:
            st.warning(f"Error reading {csv_file}: {e}")
            continue
    if not all_data:
        st.error("No valid meter power data found in CSV files.")
        return
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values('time').dropna(subset=['time', 'MeterPower'])
    if combined_df.empty:
        st.error("No valid data after processing.")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=combined_df['time'],
        y=combined_df['MeterPower'],
        mode='lines',
        name='Meter Power',
        line=dict(color='#F39C12', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(243, 156, 18, 0.1)'
    ))
    fig.update_layout(
        title="Meter Power Over Time",
        xaxis_title="Time",
        yaxis_title="Meter Power (kW)",
        height=500,
        showlegend=True,
        hovermode='x unified',
        font=dict(family="Segoe UI, Arial", size=14)
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5')
    # fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5', zeroline=True, zerolinecolor='#888')
    st.plotly_chart(fig, width='stretch')
