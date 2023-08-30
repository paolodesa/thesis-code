import pandas as pd
import requests
import json
import os
from math import radians, cos, sin, asin, sqrt, inf
import argparse
from datetime import datetime as dt
from datetime import date, timedelta


EARTH_R = 6371e3


def haversine(coords1, coords2):
    lat1, lon1 = coords1
    lat2, lon2 = coords2
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2

    c = 2 * asin(sqrt(a))

    return (c * EARTH_R)


def find_closest_wmo_station(coords1):
    df = pd.read_csv(f"{os.path.dirname(os.path.abspath(__file__))}/ashrae_wmo_db.csv", sep=";")
    min_dist = inf
    closest_index = 0
    for index, coords2 in enumerate(zip(df["lat"], df["lon"])):
        dist = haversine(coords1, coords2)
        if dist < min_dist:
            closest_index = index
            min_dist = dist
    return df.iloc[closest_index, :]["wmo"]


def get_design_conditions(wmo):
    cookies = {
        'psi_calc': 'on',
        'show_station': 'off',
        'help_window': 'off',
        'attention_2': 'on',
        'ashrae_version': '2009',
        'si_ip': 'SI',
    }
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7,fr;q=0.6,la;q=0.5,de;q=0.4',
        'Connection': 'keep-alive',
        'Content-type': 'application/x-www-form-urlencoded',
        'DNT': '1',
        'Origin': 'http://ashrae-meteo.info',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
    }
    data = {
        'wmo': f'{wmo}',
        'ashrae_version': '2009',
        'si_ip': 'SI',
    }
    res = requests.post(
        'http://ashrae-meteo.info/v2.0/request_meteo_parametres.php',
        cookies=cookies,
        headers=headers,
        data=data,
        verify=False,
    )
    decoded_data = res.text.encode().decode('utf-8-sig')
    data = json.loads(decoded_data)["meteo_stations"][0]
    tz = data["time_zone"]
    return tz, f'DESIGN CONDITIONS,1,Climate Design Data 2009 ASHRAE Handbook,,Heating,{data["coldest_month"]},{data["heating_DB_99.6"]},{data["heating_DB_99"]},{data["humidification_DP/MCDB_and_HR_99.6_DP"]},{data["humidification_DP/MCDB_and_HR_99.6_HR"]},{data["humidification_DP/MCDB_and_HR_99.6_MCDB"]},{data["humidification_DP/MCDB_and_HR_99_DP"]},{data["humidification_DP/MCDB_and_HR_99_HR"]},{data["humidification_DP/MCDB_and_HR_99_MSDB"]},{data["coldest_month_WS/MSDB_0.4_WS"]},{data["coldest_month_WS/MSDB_0.4_MCDB"]},{data["coldest_month_WS/MSDB_1_WS"]},{data["coldest_month_WS/MSDB_1_MCDB"]},{data["MCWS/PCWD_to_99.6_DB_MCWS"]},{data["MCWS/PCWD_to_99.6_DB_PCWD"]},Cooling,{data["hottest_month"]},{data["hottest_month_DB_range"]},{data["cooling_DB_MCWB_0.4_DB"]},{data["cooling_DB_MCWB_0.4_MCWB"]},{data["cooling_DB_MCWB_1_DB"]},{data["cooling_DB_MCWB_1_MCWB"]},{data["cooling_DB_MCWB_2_DB"]},{data["cooling_DB_MCWB_2_MCWB"]},{data["evaporation_WB_MCDB_0.4_WB"]},{data["evaporation_WB_MCDB_0.4_MCDB"]},{data["evaporation_WB_MCDB_1_WB"]},{data["evaporation_WB_MCDB_1_MCDB"]},{data["evaporation_WB_MCDB_2_WB"]},{data["evaporation_WB_MCDB_2_MCDB"]},{data["MCWS_PCWD_to_0.4_DB_MCWS"]},{data["MCWS_PCWD_to_0.4_DB_PCWD"]},{data["dehumidification_DP/MCDB_and_HR_0.4_DP"]},{data["dehumidification_DP/MCDB_and_HR_0.4_HR"]},{data["dehumidification_DP/MCDB_and_HR_0.4_MCDB"]},{data["dehumidification_DP/MCDB_and_HR_1_DP"]},{data["dehumidification_DP/MCDB_and_HR_1_HR"]},{data["dehumidification_DP/MCDB_and_HR_1_MCDB"]},{data["dehumidification_DP/MCDB_and_HR_2_DP"]},{data["dehumidification_DP/MCDB_and_HR_2_HR"]},{data["dehumidification_DP/MCDB_and_HR_2_MCDB"]},{data["enthalpy_MCDB_0.4_enth"]},{data["enthalpy_MCDB_0.4_MCDB"]},{data["enthalpy_MCDB_1_enth"]},{data["enthalpy_MCDB_1_MCDB"]},{data["enthalpy_MCDB_2_enth"]},{data["enthalpy_MCDB_2_MCDB"]},{data["hours_8_to_4_and_12.8/20.6"]},Extremes,{data["extreme_annual_WS_1"]},{data["extreme_annual_WS_2.5"]},{data["extreme_annual_WS_5"]},{data["extreme_max_WB"]},{data["extreme_annual_DB_mean_min"]},{data["extreme_annual_DB_mean_max"]},{data["extreme_annual_DB_standard_deviation_min"]},{data["extreme_annual_DB_standard_deviation_max"]},{data["n-year_return_period_values_of_extreme_DB_5_min"]},{data["n-year_return_period_values_of_extreme_DB_5_max"]},{data["n-year_return_period_values_of_extreme_DB_10_min"]},{data["n-year_return_period_values_of_extreme_DB_10_max"]},{data["n-year_return_period_values_of_extreme_DB_20_min"]},{data["n-year_return_period_values_of_extreme_DB_20_max"]},{data["n-year_return_period_values_of_extreme_DB_50_min"]},{data["n-year_return_period_values_of_extreme_DB_50_max"]}'


def get_te_periods(df, year):
    df_summer = df[(df.index.date >= date(year, 6, 1)) & (
        df.index.date <= date(year, 8, 31))].resample("1D").mean()
    df_winter1 = df[df.index.date < date(year, 3, 1)].resample("1D").mean()
    df_winter2 = df[df.index.date >= date(year, 12, 1)].resample("1D").mean()
    df_winter = df[(df.index.date < date(year, 3, 1)) | (
        df.index.date >= date(year, 12, 1))].resample("1D").mean()
    df_spring = df[(df.index.date >= date(year, 3, 1)) & (
        df.index.date <= date(year, 5, 31))].resample("1D").mean()
    df_autumn = df[(df.index.date >= date(year, 9, 1)) & (
        df.index.date <= date(year, 11, 30))].resample("1D").mean()

    df_summer["T_db_rolling_avg_7days"] = df_summer["T_db[C]"].rolling(
        7).mean()
    df_winter1["T_db_rolling_avg_7days"] = df_winter1[[
        "T_db[C]"]].rolling(7).mean()
    df_winter2["T_db_rolling_avg_7days"] = df_winter2[[
        "T_db[C]"]].rolling(7).mean()
    df_spring["T_db_rolling_avg_7days"] = df_spring[[
        "T_db[C]"]].rolling(7).mean()
    df_autumn["T_db_rolling_avg_7days"] = df_autumn[[
        "T_db[C]"]].rolling(7).mean()

    max_summer = df_summer[["T_db[C]"]].max().values[0]
    mean_summer = df_summer[["T_db[C]"]].mean().values[0]

    min_winter = df_winter[["T_db[C]"]].min().values[0]
    mean_winter = df_winter[["T_db[C]"]].mean().values[0]

    mean_spring = df_spring[["T_db[C]"]].mean().values[0]
    mean_autumn = df_autumn[["T_db[C]"]].mean().values[0]

    deltadays = timedelta(days=6)

    ### SUMMER ###
    min_delta_T = inf
    period_end = None
    for idx, row in df_summer.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - max_summer)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    period_start = period_end - deltadays
    extreme_summer_week = f"Summer - Week Nearest Max Temperature For Period,Extreme,{period_start.month}/{period_start.day},{period_end.month}/{period_end.day}"

    min_delta_T = inf
    period_end = None
    for idx, row in df_summer.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - mean_summer)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    period_start = period_end - deltadays
    typical_summer_week = f"Summer - Week Nearest Average Temperature For Period,Typical,{period_start.month}/{period_start.day},{period_end.month}/{period_end.day}"

    ### WINTER ###
    min_delta_T = inf
    period_end = None
    for idx, row in df_winter1.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - min_winter)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    for idx, row in df_winter2.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - min_winter)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    period_start = period_end - deltadays
    extreme_winter_week = f"Winter - Week Nearest Min Temperature For Period,Extreme,{period_start.month}/{period_start.day},{period_end.month}/{period_end.day}"

    min_delta_T = inf
    period_end = None
    for idx, row in df_winter1.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - mean_winter)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    for idx, row in df_winter2.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - mean_winter)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    period_start = period_end - deltadays
    typical_winter_week = f"Winter - Week Nearest Average Temperature For Period,Typical,{period_start.month}/{period_start.day},{period_end.month}/{period_end.day}"

    ### SPRING ###
    min_delta_T = inf
    period_end = None
    for idx, row in df_spring.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - mean_spring)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    period_start = period_end - deltadays
    typical_spring_week = f"Spring - Week Nearest Average Temperature For Period,Typical,{period_start.month}/{period_start.day},{period_end.month}/{period_end.day}"

    ### AUTUMN ###
    min_delta_T = inf
    period_end = None
    for idx, row in df_autumn.iloc()[6:, :].iterrows():
        delta_T = abs(row["T_db_rolling_avg_7days"] - mean_autumn)
        if delta_T < min_delta_T:
            period_end = idx
            min_delta_T = delta_T
    period_start = period_end - deltadays
    typical_autumn_week = f"Autumn - Week Nearest Average Temperature For Period,Typical,{period_start.month}/{period_start.day},{period_end.month}/{period_end.day}"

    return f"TYPICAL/EXTREME PERIODS,6,{extreme_summer_week},{typical_summer_week},{extreme_winter_week},{typical_winter_week},{typical_autumn_week},{typical_spring_week}"


def get_location_data(city, state, country, source, wmo, lat, lon, tz):
    res = requests.get(
        f"https://api.opentopodata.org/v1/aster30m?locations={lat},{lon}")
    elevation = res.json()["results"][0]["elevation"]
    return f"LOCATION,{city},{state},{country},{source},{wmo},{lat},{lon},{tz},{elevation}"


def get_ground_temps(lat, lon, start_date, end_date):
    df = pd.read_csv(
        f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly=soil_temperature_0_to_7cm,soil_temperature_7_to_28cm,soil_temperature_28_to_100cm,soil_temperature_100_to_255cm&timezone=Europe%2FBerlin&format=csv", header=2)
    df.index = pd.to_datetime(df['time'])
    df.drop(columns=['time'], inplace=True)
    df = df.resample("1M").mean()
    soil_temps = "GROUND TEMPERATURES,4"
    depths = ["0.04", "0.18", "0.64", "1.77"]
    for idx, depth in enumerate(df):
        soil_temps += f",{depths[idx]},,,"
        for val in df[[depth]].values:
            soil_temps += f",{round(val[0], 2)}"
    return soil_temps


def compile_header(df, city, country, lat, lon, state="", source="", leap=False, dst_start_date="0", dst_end_date="0", start_weekday="Monday", comment1="", comment2=""):
    start_date = df.index[0].strftime("%Y-%m-%d")
    end_date = df.index[-1].strftime("%Y-%m-%d")

    wmo = find_closest_wmo_station((lat, lon))
    tz, design_conditions = get_design_conditions(wmo)
    te_periods = get_te_periods(df, dt.fromisoformat(start_date).year)
    location_data = get_location_data(
        city, state, country, source, wmo, lat, lon, tz)
    ground_temps = get_ground_temps(lat, lon, start_date, end_date)

    isLeap = "Yes" if leap else "No"
    holidays_dst_data = f"HOLIDAYS/DAYLIGHT SAVINGS,{isLeap},{dst_start_date},{dst_end_date},0"

    comments1 = f"COMMENTS 1,{comment1}"
    comments2 = f"COMMENTS 2,{comment2}"

    start = dt.fromisoformat(start_date)
    end = dt.fromisoformat(end_date)
    data_periods = f"DATA PERIODS,1,1,Data,{start_weekday},{start.month}/{start.day}/{start.year},{end.month}/{end.day}/{end.year}"

    header = f"{location_data}\n{design_conditions}\n{te_periods}\n{ground_temps}\n{holidays_dst_data}\n{comments1}\n{comments2}\n{data_periods}"
    return header


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", help="City", required=True)
    parser.add_argument(
        "--country", help="Country code (e.g. ITA)", required=True)
    parser.add_argument("--lat", help="Latitude", type=float, required=True)
    parser.add_argument("--lon", help="Longitude", type=float, required=True)
    parser.add_argument(
        "--filename", help="Path of the weather data in csv format", required=True)
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
    return args.city, args.country, args.lat, args.lon, args.filename, args.state, args.source, args.leap, args.dst_start_date, args.dst_end_date, args.start_weekday, args.comment1, args.comment2


if __name__ == "__main__":
    city, country, lat, lon, filename, state, source, leap, dst_start_date, dst_end_date, start_weekday, comment1, comment2 = parse_args()

    header = compile_header(city, country, lat, lon, filename, state, source, leap, dst_start_date, dst_end_date, start_weekday, comment1, comment2)
    print(header)
