from pyepw.epw import EPW
import pyepw
import pandas as pd
import argparse
from header_compiler.header_compiler import compile_header
from influxdb_client import InfluxDBClient
import ast
from wu_data_cleaner import clean_data
from epw_data_compiler import compile_epw_data
import os
from dotenv import load_dotenv


load_dotenv()
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
WEATHER_UNDERGROUND_BUCKET_NAME = os.getenv('WEATHER_UNDERGROUND_BUCKET_NAME')

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()


def fix_dates(epw):
    first_date = epw.weatherdata[0]
    if first_date.hour != 1:
        data = pd.DataFrame()
        for i in range(first_date.hour-1):
            data = data.append({
                    "year": first_date.year,
                    "month": first_date.month,
                    "day": first_date.day,
                    "hour": i+1,
                    "minute": first_date.minute
                }, ignore_index=True)
        data = data.astype(int).astype(str)

        for pos in reversed(range(len(data))):
            epw.weatherdata.insert(0, pyepw.epw.WeatherData())
            values = data.iloc[pos].values
            empty_values = ["" for _ in range(35 - len(values))]
            new_values = list(values) + list(empty_values)
            epw.weatherdata[0].read(vals=new_values)

    return epw


def empty_strings(df):
    """Generate a list of empty strings which is as long as the dataframe.

    :param df: DataFrame
    :type df: class pandas.core.frame.DataFrame
    :return: List of empty strings
    :rtype: list
    """
    return ["" for _ in range(len(df))]


def convert_dates(date):
    """Convert date from (0-23 h) and (0-59 min) to (1-24 h) and (1-60 min).

    :param date: Timestamp
    :type date: pandas._libs.tslibs.timestamps.Timestamp
    :return: A tuple made of (year, month, day, hour, minute)
    :rtype: tuple
    """
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour + 1  # To make hour compatible with EnergyPlus
    minute = date.minute

    return (year, month, day, hour, minute)


def convert_to_epw(
        df,
        header,
        station_id
    ):
    """Load a CSV file and generate a correspondent EPW file.

    :param csv_path: Path to CSV file
    :type csv_path: `str` or `Path`
    :param header: Raw EPW header string
    :type header_rows: `str`
    :return: EPW object
    :rtype: class:`pyepw.epw.EPW`
    """

    # Generate empty EPW and add header rows.
    epw = EPW()
    epw.location = pyepw.epw.Location()
    epw.design_conditions = pyepw.epw.DesignCondition()
    epw.typical_or_extreme_periods = pyepw.epw.TypicalOrExtremePeriods()
    epw.ground_temperatures = pyepw.epw.GroundTemperatures()
    epw.holidays_or_daylight_savings = pyepw.epw.HolidaysOrDaylightSavings()
    epw.comments_1 = pyepw.epw.Comments1()
    epw.comments_2 = pyepw.epw.Comments2()
    epw.data_periods = pyepw.epw.DataPeriods()

    # Fill EPW with CSV data.
    epw_df = pd.DataFrame(
        {
            "year": [convert_dates(x)[0] for x in df.index],
            "month": [convert_dates(x)[1] for x in df.index],
            "day": [convert_dates(x)[2] for x in df.index],
            "hour": [convert_dates(x)[3] for x in df.index],
            "minute": [convert_dates(x)[4] + 1 for x in df.index],
            "data_source_and_uncertainty_flags": empty_strings(df),
            "dry_bulb_temperature": df["T_db[C]"],
            "dew_point_temperature": df["T_dp[C]"],
            "relative_humidity": df["RH[%]"]
            .replace("", 999)
            .astype(int)
            .replace(999, ""),
            "atmospheric_station_pressure": (
                df["P_atm[hPa]"] * 100
            )  # hPa to Pa
            .replace("", 999999)
            .astype(int)
            .replace(999999, ""),
            "extraterrestrial_horizontal_radiation": empty_strings(df),
            "extraterrestrial_direct_normal_radiation": empty_strings(df),
            "horizontal_infrared_radiation_intensity": df["HIRI[W/m2]"],
            "global_horizontal_radiation": empty_strings(df),
            "direct_normal_radiation": df["DNI[W/m2]"],
            "diffuse_horizontal_radiation": df["DIF[W/m2]"],
            "global_horizontal_illuminance": empty_strings(df),
            "direct_normal_illuminance": empty_strings(df),
            "diffuse_horizontal_illuminance": empty_strings(df),
            "zenith_luminance": empty_strings(df),
            "wind_direction": df["wind_dir[o]"],
            "wind_speed": df["v_air[m/s]"],
            "total_sky_cover": empty_strings(df),
            "opaque_sky_cover": empty_strings(df),
            "visibility": empty_strings(df),
            "ceiling_height": empty_strings(df),
            "present_weather_observation": df[
                "present_weather_observation"
            ].astype(int),
            "present_weather_codes": empty_strings(
                df
            ),  # df["present_weather_codes"],
            "precipitable_water": empty_strings(df),
            "aerosol_optical_depth": empty_strings(df),
            "snow_depth": empty_strings(df),
            "days_since_last_snowfall": empty_strings(df),
            "albedo": empty_strings(df),
            "liquid_precipitation_depth": df["rain[mm]"],
            "liquid_precipitation_quantity": empty_strings(df),
        }
    )
    epw_df.reset_index(drop=True, inplace=True)
    for r in range(len(df)):
        data = [str(x) for x in epw_df.loc[r].values]
        epw.weatherdata.append(pyepw.epw.WeatherData())
        epw.weatherdata[-1].read(vals=data)

    epw = fix_dates(epw)

    # Save EPW
    epw.save(f'{station_id}.epw')
    # Replace header
    with open(f'{station_id}.epw', "r+") as f:
        data = f.readlines()
        data = data[8:]
        data.insert(0, f"{header}\n")
        f.seek(0)
        for d in data:
            f.write(d)
        f.close()
    print("SAVING TO:", f'{station_id}.epw')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Weather station ID", required=True)
    parser.add_argument("--year", type=int, help="Year", required=True)
    parser.add_argument("--city", help="City", required=True)
    parser.add_argument(
        "--country", help="Country code (e.g. ITA)", required=True)
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
    return args.id.upper(), args.year, args.city, args.country, args.state, args.source, args.leap, args.dst_start_date, args.dst_end_date, args.start_weekday, args.comment1, args.comment2


if __name__ == "__main__":
    station_id, year, city, country, state, source, leap, dst_start_date, dst_end_date, start_weekday, comment1, comment2 = parse_args()

    query = f'from(bucket:"{WEATHER_UNDERGROUND_BUCKET_NAME}")\
        |> range(start: {year-1}-12-31T23:59:00Z, stop: {year}-12-31T23:59:59Z)\
        |> filter(fn: (r) => r["_measurement"] == "{station_id}")\
        |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)\
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

    df = query_api.query_data_frame(query)
    df.index = pd.to_datetime(df['_time'])
    df.sort_index(inplace=True)

    df['lat'] = df.apply(lambda row: ast.literal_eval(row.coords)[0], axis=1)
    df['lon'] = df.apply(lambda row: ast.literal_eval(row.coords)[1], axis=1)
    lat = df['lat'].max()
    lon = df['lon'].max()
    
    df.drop(columns=['result', 'table', '_start', '_stop', '_time', 'coords', '_measurement', 'lat', 'lon'], inplace=True)

    df = clean_data(df, year)
    
    header = compile_header(
        df, city, country, lat, lon, state, source, leap, dst_start_date, dst_end_date, start_weekday, comment1, comment2
    )

    convert_to_epw(
        df=compile_epw_data(df, lat, lon),
        header=header,
        station_id=station_id
    )      