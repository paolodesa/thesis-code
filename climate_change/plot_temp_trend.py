import argparse
import pandas as pd
from influxdb_client import InfluxDBClient
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14


load_dotenv()
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

parser = argparse.ArgumentParser()
parser.add_argument("--id", help="Weather station ID", required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year", type=int, required=True)
args = parser.parse_args()

station_id, start_year, end_year = args.id.upper(), args.start_year, args.end_year

fig = plt.figure(figsize=(16, 9))

for source in ['WeatherUnderground', 'OpenMeteo']:
    query = f'from(bucket:"{source}")\
            |> range(start: {start_year-1}-12-31T23:59:00Z, stop: {end_year}-12-31T23:59:59Z)\
            |> filter(fn: (r) => r["_measurement"] == "{station_id}")\
            |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)\
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
    
    df = query_api.query_data_frame(query)
    df.index = pd.to_datetime(df['_time'])
    df.sort_index(inplace=True)
    df = df.resample('Y').mean(numeric_only=True)
    
    years = range(start_year, end_year+1)
    plt.plot(years, df['T_db[C]'], label=source)

plt.xlabel('Year')
plt.ylabel('Mean dry-bulb air temperature [°C]')
plt.legend()
plt.show()