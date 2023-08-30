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

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

parser = argparse.ArgumentParser()
parser.add_argument("--id", help="Weather station ID", required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year", type=int, required=True)
args = parser.parse_args()

station_id, start_year, end_year = args.id.upper(), args.start_year, args.end_year

for source in ['WeatherUnderground', 'OpenMeteo']:
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

    df2 = df

    climate_params = [
        "T_db[C]", 
        "GHI[W/m2]",
        "RH[%]",
        "v_air[m/s]"
    ]
    df = df[climate_params]

    df = df.resample("1D").mean()

    df["month"] = df.index.month
    df["year"] = df.index.year
    df["PHI"] = np.nan
    df["F"] = np.nan

    df_fs = df.resample("1M").mean()
    df_fs = df_fs[["year", "month", "v_air[m/s]"]]
    for cp in climate_params:
        df_fs[f"F_S_{cp}"] = np.nan 

    for cp in climate_params:
        dfs_by_month = df.groupby(pd.Grouper(key="month"))
        # groups to a list of dataframes with list comprehension
        dfs_by_month = [group.sort_values(f'{cp}')
                        for _, group in dfs_by_month]
        for df_by_month in dfs_by_month:
            df_by_month["PHI"] = [i/(len(df_by_month+1))
                                for i in range(1, len(df_by_month)+1)]
            df = df.combine_first(df_by_month[["PHI"]])

        dfs_by_year = df.groupby(pd.Grouper(freq="Y"))
        dfs_by_year = [group for _, group in dfs_by_year]
        for df_by_year in dfs_by_year:
            dfs_by_month = df_by_year.groupby(pd.Grouper(key="month"))
            dfs_by_month = [group.sort_values(f'{cp}')
                            for _, group in dfs_by_month]
            for df_by_month in dfs_by_month:
                df_by_month["F"] = [i/(len(df_by_month+1))
                                    for i in range(1, len(df_by_month)+1)]
                df = df.combine_first(df_by_month[["F"]])

        dfs_by_month_year = df.groupby(pd.Grouper(freq="M"))
        dfs_by_month_year = [(key, group) for key, group in dfs_by_month_year]

        for key, df_by_month_year in dfs_by_month_year:
            val = abs(df_by_month_year["F"] - df_by_month_year["PHI"]).resample("1M").sum().iloc()[0]
            df_fs.loc[key][f"F_S_{cp}"] = val
            
    df_fs["F_S_tot"] = df_fs[f"F_S_{climate_params[0]}"] + df_fs[f"F_S_{climate_params[1]}"] + df_fs[f"F_S_{climate_params[2]}"]
    df_fs_by_month = df_fs.groupby(pd.Grouper(key="month"))
    df_fs_by_month = [group.sort_values(f'F_S_tot')
                    for _, group in df_fs_by_month]

    typical_months = []
    for d in df_fs_by_month:
        d = d.iloc[:3]
        d["windspeedDev"] = abs(d["v_air[m/s]"] - d["v_air[m/s]"].mean())
        d = d.sort_values("windspeedDev")
        typical_months.append(d.index[0])

    df = df2
    dfs_typical = []
    for ts in typical_months:
        dfs_typical.append(df[(df.index.year == ts.year) & (df.index.month == ts.month)])
    for idx, d in enumerate(dfs_typical):
        if (idx == 0):
            final_df = d
        else:
            final_df = pd.concat([final_df, d])
    final_df.index = final_df.index.map(lambda x: x.replace(year = 1970))
    final_df = final_df.resample("1H").mean()
    final_df.to_csv(f"{station_id}_ISO_TMY_{source}_{start_year}_{end_year}.csv", index=True)
