import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import glob
import os

def display_total_power_export():
    # Time range selection
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.time_input("Start Time", value=pd.Timestamp("17:00").time())
    with col2:
        end_time = st.time_input("End Time", value=pd.Timestamp("21:00").time())
    # st.header("⚡ Total Power Export")

    def trapezoidal_daily_export(df):
        """Calculate daily cumulative export using trapezoidal integration (MeterPower in kW)."""
        df = df.copy()
        df['date'] = df['time'].dt.date
        df['Cumulative_Export_kWh'] = 0.0
        for day, group in df.groupby('date'):
            group = group.sort_values('time')
            times = group['time'].astype('int64') // 10**9  # seconds
            powers = -group['MeterPower'].values  # kW, positive for export
            energy = [0]
            for i in range(1, len(times)):
                dt = times.iloc[i] - times.iloc[i-1]
                avg_power = (powers[i-1] + powers[i]) / 2
                # kWh = kW * h
                energy.append(energy[-1] + (avg_power * dt) / 3600)  # kWh
            df.loc[group.index, 'Cumulative_Export_kWh'] = energy
        return df
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
                # Only keep negative (export) values
                df_export = df[df['MeterPower'] < 0].copy()
                if not df_export.empty:
                    all_data.append(df_export)
        except Exception as e:
            st.warning(f"Error reading {csv_file}: {e}")
            continue
    if not all_data:
        st.error("No valid export power data found in CSV files.")
        return
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values('time').dropna(subset=['time', 'MeterPower'])
    if combined_df.empty:
        st.error("No valid export data after processing.")
        return

    # Filter each day's data to the selected time range
    def filter_time_range(df, start_time, end_time):
        df = df.copy()
        df['time_only'] = df['time'].dt.time
        return df[(df['time_only'] >= start_time) & (df['time_only'] <= end_time)]

    filtered_df = pd.DataFrame()
    for day, group in combined_df.groupby(combined_df['time'].dt.date):
        group_filtered = filter_time_range(group, start_time, end_time)
        filtered_df = pd.concat([filtered_df, group_filtered], ignore_index=True)

    if filtered_df.empty:
        st.warning("No export data found in the selected time range.")
        return

    # Use trapezoidal integration for daily cumulative export
    filtered_df = trapezoidal_daily_export(filtered_df)

    fig = go.Figure()
    today = pd.Timestamp.now(tz='Australia/Sydney').date()
    total_export_today = 0
    for day, group in filtered_df.groupby('date'):
        fig.add_trace(go.Scatter(
            x=group['time'],
            y=group['Cumulative_Export_kWh'],
            mode='lines',
            name=str(day),
            line=dict(width=2),
            marker=dict(size=6),
            fill='tozeroy',
            fillcolor='rgba(39, 174, 96, 0.1)'
        ))
        if day == today and not group.empty:
            total_export_today = group['Cumulative_Export_kWh'].iloc[-1]
    fig.update_layout(
        title="Daily Power Exported to Grid (Cumulative per Day)",
        xaxis_title="Time",
        yaxis_title="Cumulative Export (kWh)",
        height=500,
        showlegend=True,
        hovermode='x unified',
        font=dict(family="Segoe UI, Arial", size=14)
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5', zeroline=True, zerolinecolor='#888')
    st.plotly_chart(fig, width='stretch')
    total_export_today_wh = total_export_today * 1000
    st.markdown(f"**Total Power Exported Today:** {total_export_today_wh:.0f} Wh")
