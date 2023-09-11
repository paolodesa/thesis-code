import pandas as pd
import numpy as np
import argparse
from influxdb_client import InfluxDBClient
import os
from dotenv import load_dotenv


load_dotenv()
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
WEATHER_UNDERGROUND_BUCKET_NAME = os.getenv('WEATHER_UNDERGROUND_BUCKET_NAME')
OPEN_METEO_BUCKET_NAME = os.getenv('OPEN_METEO_BUCKET_NAME')

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

parser = argparse.ArgumentParser()
parser.add_argument("--id", help="Weather station ID", required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year", type=int, required=True)
args = parser.parse_args()

station_id, start_year, end_year = args.id.upper(), args.start_year, args.end_year

for source in [WEATHER_UNDERGROUND_BUCKET_NAME, OPEN_METEO_BUCKET_NAME]:
    query = f'from(bucket:"{source}")\
            |> range(start: {start_year-1}-12-31T23:59:00Z, stop: {end_year}-12-31T23:59:59Z)\
            |> filter(fn: (r) => r["_measurement"] == "{station_id}")\
            |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)\
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

    df = query_api.query_data_frame(query)
    df.index = pd.to_datetime(df['_time'])
    df.index = df.index.tz_localize(None)
    df.sort_index(inplace=True)

    df.drop(columns=['result', 'table', '_start', '_stop', '_time', 'coords', '_measurement'], inplace=True)

    # Set the desired time range
    start_date = f'{start_year}-01-01 00:00:00'
    end_date = f'{end_year}-12-31 23:59:59'

    # Create a DateTimeIndex with hourly frequency
    hourly_range = pd.date_range(start=start_date, end=end_date, freq='H')

    # Create an empty DataFrame with the DateTimeIndex
    df_filled = pd.DataFrame(index=hourly_range)

    # Merge the empty DataFrame with your original data
    df_merged = df_filled.merge(df, left_index=True, right_index=True, how='left')

    # Forward-fill missing values with previous value at the same hour
    df_filled = df_merged.groupby([df_merged.index.hour]).ffill()

    # Backward-fill remaining missing values
    df_filled = df_filled.groupby([df_merged.index.hour]).bfill()

    df = df_filled.rename_axis('timestamp')

    df.drop(df.index[df.index.month.isin([2]) & df.index.day.isin([29])], inplace=True)
    df.resample("1H").mean()
    df = df.groupby('{:%m-%d %H}'.format).mean()
    df.index = pd.to_datetime(df.index.map(lambda x: "1970-" + x + ":00:00"))
    df.to_csv(f"{station_id}_mean_TMY_{source}_{start_year}_{end_year}.csv", index=True)