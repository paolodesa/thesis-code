import pandas as pd
import argparse
import numpy as np
import argparse
import scipy
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
        epw_filename=f"{lat}_{lon}_mean_TMY_{start_year}_{end_year}"
    )


def mode_std(x):
    mode_array = scipy.stats.mode(x, keepdims=True)[0]
    if len(mode_array) == 0:
        return np.nan
    elif np.isnan(mode_array):
        return np.nan
    else:
        return mode_array[0]

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

df.drop(df.index[df.index.month.isin([2]) & df.index.day.isin([29])], inplace=True)

resample_dict = {
    "v_air[m/s]": "mean",
    "wind_dir[o]": lambda x: mode_std(x),
    "T_db[C]": "mean",
    "T_dp[C]": "mean",
    "RH[%]": "mean",
    "P_atm[hPa]": "mean",
    "rain[mm]": "mean",
    "GHI[W/m2]": "mean",
    "soil_temperature_0_to_7cm (°C)": "mean",
    "soil_temperature_7_to_28cm (°C)": "mean",
    "soil_temperature_28_to_100cm (°C)": "mean",
    "soil_temperature_100_to_255cm (°C)": "mean"
}
df = df.groupby('{:%m-%d %H}'.format).agg(resample_dict)

df.index = pd.to_datetime(df.index.map(lambda x: "1970-" + x + ":00:00"))
df.to_csv(f"{lat}_{lon}_mean_TMY_{start_year}_{end_year}.csv", index=True)

if epw:
    to_epw(df)