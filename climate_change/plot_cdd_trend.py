import argparse
import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv


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


def cdd(df):
    """Compute Cooling Degree Days.

    :param df: DataFrame containing a timestamp index and "T_db_o[C]"
        column
    :type df: class:`pandas.core.frame.DataFrame`
    :return: Cooling degree days
    :rtype: float
    """
    
    df["cdd"] = df["T_db_o[C]"]-21
    sum_dist = df["cdd"].where((df["T_db_o[C]"]-24)>=0).sum()

    return sum_dist


for source in ['WeatherUnderground', 'OpenMeteo']:
    query = f'from(bucket:"{source}")\
                |> range(start: {start_year-1}-12-31T23:59:00Z, stop: {end_year}-12-31T23:59:59Z)\
                |> filter(fn: (r) => r["_measurement"] == "{station_id}")\
                |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)\
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
        
    df = query_api.query_data_frame(query)
    df.index = pd.to_datetime(df['_time'])
    df.sort_index(inplace=True)

    df['T_db_o[C]'] = df["T_db[C]"]
    df = df.resample("1D").mean(numeric_only=True)
    df = df[~((df.index.month == 2) & (df.index.day == 29))]

    cdds = []
    years = range(start_year, end_year+1)
    for y in years:
        cdds.append(cdd(df[df.index.year == y]))

    plt.plot(years, cdds, label=source)

plt.title(f"CDD for station {station_id}")
plt.xlabel("Year")
plt.ylabel("CDD")
plt.legend()
plt.show()