import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14
import numpy as np
from influxdb_client import InfluxDBClient
from pyepw.epw import EPW
from dotenv import load_dotenv


load_dotenv()
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
WEATHER_UNDERGROUND_BUCKET_NAME = os.getenv('WEATHER_UNDERGROUND_BUCKET_NAME')

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

parser = argparse.ArgumentParser()
parser.add_argument("--id", help="ID of the weather station you want to use for comparison", required=True)
parser.add_argument("--filename", help="Filename of the EPW you want to use for comparison", required=True)
args = parser.parse_args()
station_id = args.id

epw = EPW()
epw.read(f"{args.filename}")

init_datapoint = epw.weatherdata[0]
final_datapoint = epw.weatherdata[-1]

init_month = f"{int(init_datapoint.month):02d}"
init_day = f"{int(init_datapoint.day):02d}"
init_hour = f"{(int(init_datapoint.hour)-2):02d}"
final_month = f"{int(final_datapoint.month):02d}"
final_day = f"{int(final_datapoint.day):02d}"
final_hour = f"{(int(final_datapoint.hour)-1):02d}"

start_ts = f"{init_datapoint.year}-{init_month}-{init_day}T{init_hour}:00:00Z"
end_ts = f"{final_datapoint.year}-{final_month}-{final_day}T{final_hour}:00:00Z"

query = f'from(bucket:"{WEATHER_UNDERGROUND_BUCKET_NAME}")\
    |> range(start: {start_ts}, stop: {end_ts})\
    |> filter(fn: (r) => r["_measurement"] == "{station_id}")\
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)\
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

df = query_api.query_data_frame(query)
df.index = pd.to_datetime(df['_time'])
df.index = df.index.tz_localize(None)
df = df.resample("1H").mean(numeric_only=True)
df['epw_tdb'] = [float(ws.dry_bulb_temperature) for ws in epw.weatherdata]

def pearson_corr_coeff(X, Y):
    X_diff = X - np.nanmean(X)
    Y_diff = Y - np.nanmean(Y)
    numerator = np.nansum(X_diff * Y_diff)
    denominator = np.sqrt(np.nansum(X_diff ** 2)) * np.sqrt(np.nansum(Y_diff ** 2))
    return numerator / denominator

print(f"Mean distance between time series (dry-bulb air temperature): {round(np.nanmean(df['epw_tdb'] - df['T_db[C]'].values), 3)} °C")
print(f"Pearson correlation coefficient (dry-bulb air temperature): {round(pearson_corr_coeff(df['epw_tdb'], df['T_db[C]'].values), 3)}")

df = df.resample("1D").mean(numeric_only=True)

fig = plt.figure(figsize=(16, 9))
plt.plot(df.index, df['T_db[C]'], label=f"{station_id} WS")
plt.plot(df.index, df['epw_tdb'], label="Politecnico di Torino's WS")
plt.xlabel("Timestamp")
plt.ylabel("Dry-bulb air temperature [°C]")
plt.legend()
plt.show()