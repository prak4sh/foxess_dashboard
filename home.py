import streamlit as st
import subprocess
import json
import pandas as pd

def display_home():
	st.header("Home Dashboard")
	# Run query.py and parse output
	query_result = subprocess.run(["python", "scripts/query.py"], capture_output=True, text=True)
	try:
		query_json = json.loads(query_result.stdout)
		st.success("Live inverter data fetched successfully.")
		# Display summary info
		if 'result' in query_json and query_json['result']:
			data = query_json['result'][0]
			st.markdown(f"**Device SN:** `{data.get('deviceSN', '')}`  ")
			st.markdown(f"**Time:** `{data.get('time', '')}`  ")
			st.markdown("---")
			# Show key metrics in columns
			key_metrics = [
				("SoC", "%"), ("batTemperature", "℃"), ("batVolt", "V"), ("batCurrent", "A"),
				("MeterPower", "kW"), ("feedinPower", "kW"), ("gridConsumptionPower", "kW"),
				("batChargePower", "kW"), ("batDischargePower", "kW"), ("loadsPower", "kW"),
				("generationPower", "kW"), ("ambientTemperation", "℃"), ("invTemperation", "℃")
			]
			values = {d['variable']: d['value'] for d in data['datas']}
			units = {d['variable']: d.get('unit', '') for d in data['datas']}
			cols = st.columns(4)
			for i, (var, default_unit) in enumerate(key_metrics):
				val = values.get(var, None)
				unit = units.get(var, default_unit)
				if val is not None:
					cols[i % 4].metric(var, f"{val} {unit}")
			st.markdown("---")
			# Show all data in a nice table
			df = []
			for d in data['datas']:
				df.append({
					"Name": d.get('name', d.get('variable', '')),
					"Value": str(d.get('value', '')),
					"Unit": d.get('unit', '')
				})
			df = pd.DataFrame(df)
			st.dataframe(df, hide_index=True, width='stretch')
		else:
			st.warning("No data found in query output.")
	except Exception as e:
		st.error(f"Failed to parse query.py output: {e}")
		st.code("STDOUT:\n" + query_result.stdout)
		st.code("STDERR:\n" + query_result.stderr)
		st.code(f"Return code: {query_result.returncode}")
	st.markdown("---")
	if st.button("Run History Script"):
		result = subprocess.run(["python", "scripts/history.py"], capture_output=True, text=True)
		st.rerun()
