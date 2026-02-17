import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import glob
import os

def display_battery_summary():
    # st.header("📈 Battery Summary")
    history_folder = "history"
    csv_files = glob.glob(os.path.join(history_folder, "foxess_history_*.csv"))
    if not csv_files:
        st.warning("No battery history data found. Please run the history collection script first.")
        return
    all_data = []
    for csv_file in sorted(csv_files):
        try:
            df = pd.read_csv(csv_file)
            if not df.empty and 'time' in df.columns and 'SoC' in df.columns:
                df['time'] = pd.to_datetime(df['time'], errors='coerce', utc=True)
                df['time'] = df['time'].dt.tz_convert('Australia/Sydney')
                df['date'] = df['time'].dt.date
                all_data.append(df)
        except Exception as e:
            st.warning(f"Error reading {csv_file}: {e}")
            continue
    if not all_data:
        st.error("No valid battery data found in CSV files.")
        return
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values('time').dropna(subset=['time', 'SoC'])
    if combined_df.empty:
        st.error("No valid data after processing.")
        return
    daily_stats = combined_df.groupby('date')['SoC'].agg(['mean', 'min', 'max']).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['mean'],
        mode='lines+markers',
        name='Daily Average',
        line=dict(color='#2E86AB', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.1)'
    ))
    fig.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['max'],
        mode='lines+markers',
        name='Daily Max',
        line=dict(color='lightgreen', width=1, dash='dot'),
        marker=dict(size=6)
    ))
    fig.add_trace(go.Scatter(
        x=daily_stats['date'],
        y=daily_stats['min'],
        mode='lines+markers',
        name='Daily Min',
        line=dict(color='lightcoral', width=1, dash='dot'),
        marker=dict(size=6),
        fill='tonexty',
        fillcolor='rgba(255, 0, 0, 0.1)'
    ))
    fig.update_layout(
        title="Daily Battery SoC Statistics",
        xaxis_title="Date",
        yaxis_title="State of Charge (%)",
        height=500,
        showlegend=True,
        hovermode='x unified',
        font=dict(family="Segoe UI, Arial", size=14)
    )
    # fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e5e5e5')
    # fig.update_yaxes(range=[0, 110], showgrid=True, gridwidth=1, gridcolor='#e5e5e5', zeroline=True, zerolinecolor='#888')
    st.plotly_chart(fig, width='stretch')
