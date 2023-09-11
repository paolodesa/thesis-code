from influxdb_client import InfluxDBClient
from math import sin, cos, sqrt, atan2,radians

import pandas as pd
import matplotlib.pyplot as plt
import ast
import argparse
import os
from dotenv import load_dotenv


load_dotenv()
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
WEATHER_UNDERGROUND_BUCKET_NAME = os.getenv('WEATHER_UNDERGROUND_BUCKET_NAME')

parser = argparse.ArgumentParser()
parser.add_argument("--radius", help="Urban area radius [km]", type=float, required=True)
parser.add_argument("--lat", help="Latitude of urban area center point", type=float, required=True)
parser.add_argument("--lon", help="Longitude of urban area center point", type=float, required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year", type=int, required=True)
args = parser.parse_args()

radius, center_lat, center_lon, start_year, end_year = args.radius, args.lat, args.lon, args.start_year, args.end_year

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

query = f'from(bucket:"{WEATHER_UNDERGROUND_BUCKET_NAME}")\
    |> range(start: {start_year-1}-12-31T23:59:00Z, stop: {end_year}-12-31T23:59:59Z)\
    |> filter(fn: (r) => r["_field"] == "T_db[C]")\
    |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)\
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

df = query_api.query_data_frame(query)

df['lat'] = df.apply(lambda row: ast.literal_eval(row.coords)[0], axis=1)
df['lon'] = df.apply(lambda row: ast.literal_eval(row.coords)[1], axis=1)
df.index = pd.to_datetime(df['_time'])
df.sort_index(inplace=True)
df.drop(columns=['result', 'table', '_start', '_stop', '_time', 'coords'], inplace=True)

def filter_inner(row, lat2, lon2, max):
    if getDist(row['lat'], row['lon'], lat2, lon2) <= max:
        return True
    else:
        return False
    
def filter_outer(row, lat2, lon2, min):
    if getDist(row['lat'], row['lon'], lat2, lon2) > min:
        return True
    else:
        return False
    
def getDist(lat1, lon1, lat2, lon2):
  R = 6373.0

  lat1 = radians(lat1)
  lon1 = radians(lon1)
  lat2 = radians(lat2)
  lon2 = radians(lon2)

  dlon = lon2 - lon1
  dlat = lat2 - lat1

  a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
  c = 2 * atan2(sqrt(a), sqrt(1 - a))

  return R * c

df_inner = df[df.apply(filter_inner, args=(center_lat, center_lon, radius), axis=1)]
df_outer = df[df.apply(filter_outer, args=(center_lat, center_lon, radius), axis=1)]

inner_by_month = df_inner.groupby(df_inner.index.month)['T_db[C]'].mean()
outer_by_month = df_outer.groupby(df_outer.index.month)['T_db[C]'].mean()

inner_by_hour = df_inner.groupby(df_inner.index.hour)['T_db[C]'].mean()
outer_by_hour = df_outer.groupby(df_outer.index.hour)['T_db[C]'].mean()

plt.figure()
plt.plot(inner_by_hour - outer_by_hour)
plt.title(f"Hourly temperature gap between urban and sub-urban WSs")
plt.xlabel("Hour of day")
plt.ylabel("deltaT [°C]")

plt.figure()
plt.plot(inner_by_month - outer_by_month)
plt.title("Monthly temperature gap between urban and sub-urban WSs")
plt.xlabel("Month of year")
plt.ylabel("deltaT [°C]")

plt.show()