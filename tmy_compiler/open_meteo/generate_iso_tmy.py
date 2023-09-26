import pandas as pd
import numpy as np
import argparse
import math
import sys
sys.path.append('../../epw_compiler')
from header_compiler.header_compiler import compile_header
from epw_data_compiler import compile_epw_data
from generate_epw import convert_to_epw


parser = argparse.ArgumentParser()
parser.add_argument("--lat", help="Latitude", type=float, required=True)
parser.add_argument("--lon", help="Longitude", type=float, required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year", type=int, required=True)
parser.add_argument("--epw", help="Flag to output TMY file in EPW format", action="store_true")
parser.add_argument("--city", help="City", default="Unknown")
parser.add_argument(
    "--country", help="Country code (e.g. ITA)", default="Unknown")
parser.add_argument(
    "--state", help="State/Province/Region (optional)", default="")
parser.add_argument("--source", help="Data source (optional)", default="")
parser.add_argument(
    "--leap", help="Leap year flag (optional)", action="store_true")
parser.add_argument(
    "--dst_start_date", help="DST start date [m/d] (optional)", default="0")
parser.add_argument(
    "--dst_end_date", help="DST end date [m/d] (optional)", default="0")
parser.add_argument(
    "--start_weekday", help="Start day of the week (default=Monday)", default="Monday")
parser.add_argument(
    "--comment1", help="1st comment line (optional)", default="")
parser.add_argument(
    "--comment2", help="2nd comment line (optional)", default="")
args = parser.parse_args()

lat, lon, start_year, end_year, epw, city, country, state, source, leap, dst_start_date, dst_end_date, start_weekday, comment1, comment2 = args.lat, args.lon, args.start_year, args.end_year, args.epw, args.city, args.country, args.state, args.source, args.leap, args.dst_start_date, args.dst_end_date, args.start_weekday, args.comment1, args.comment2


def abs_humidity_from_T_and_rh(T, rh):
    # This formula includes an expression for saturation vapor pressure (Bolton 1980) accurate to 0.1% over the temperature range -30°C≤T≤35°C
    return (6.112 * pow(math.e, (17.67 * T) / (T + 243.5)) * rh * 18.02) / ((273.15 + T) * 100 * 0.08314)


def compute_rain_type(prec_total):
    if prec_total == 0.0:
        return 40
    else:
        return 61
    

def to_epw(df):
    df['abs_humidity[g/m3]'] = [abs_humidity_from_T_and_rh(T, rh) for T, rh in zip(df['T_db[C]'], df['RH[%]'])]
    df['rain_type[int]'] = [compute_rain_type(prec_total) for prec_total in df['rain[mm]']]

    header = compile_header(
        df, city, country, lat, lon, state, source, leap, dst_start_date, dst_end_date, start_weekday, comment1, comment2, use_source_for_ground=True
    )

    convert_to_epw(
        df=compile_epw_data(df, lat, lon),
        header=header,
        epw_filename=f"{lat}_{lon}_ISO_TMY_{start_year}_{end_year}"
    )


def scrape_om(lat, lon, start_year, end_year):
    df = pd.read_csv(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_year}-01-01&end_date={end_year}-12-31&hourly=temperature_2m,relativehumidity_2m,dewpoint_2m,precipitation,pressure_msl,windspeed_10m,winddirection_10m,soil_temperature_0_to_7cm,soil_temperature_7_to_28cm,soil_temperature_28_to_100cm,soil_temperature_100_to_255cm,diffuse_radiation&windspeed_unit=ms&format=csv", header=2)

    df['T_db[C]'] = df['temperature_2m (°C)']
    df['RH[%]'] = df['relativehumidity_2m (%)']
    df['v_air[m/s]'] = df['windspeed_10m (m/s)']
    df['wind_dir[o]'] = df['winddirection_10m (°)']
    df['T_dp[C]'] = df['dewpoint_2m (°C)']
    df['P_atm[hPa]'] = df['pressure_msl (hPa)']
    df['rain[mm]'] = df['precipitation (mm)']
    df['GHI[W/m2]'] = df['diffuse_radiation (W/m²)']
    
    df.drop(columns=['time', 'temperature_2m (°C)', 'relativehumidity_2m (%)', 'windspeed_10m (m/s)', 'winddirection_10m (°)', 'dewpoint_2m (°C)', 'pressure_msl (hPa)', 'precipitation (mm)', 'diffuse_radiation (W/m²)'], inplace=True)
    return df


df = scrape_om(lat, lon, start_year, end_year)

if (start_year < 1970):
    start_date = f'1970-01-01 00:00:00'
    end_date = f'{end_year+(1970-start_year)}-12-31 23:59:59'
else:
    start_date = f'{start_year}-01-01 00:00:00'
    end_date = f'{end_year}-12-31 23:59:59'

df.index = pd.date_range(start=start_date, end=end_date, freq='H')
df.index = df.index.tz_localize(None)
df = df.rename_axis('timestamp')

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
final_df.to_csv(f"{lat}_{lon}_ISO_TMY_{start_year}_{end_year}.csv", index=True)

if epw:
    to_epw(final_df)
