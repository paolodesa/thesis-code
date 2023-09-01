from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd
import argparse
import requests
import time
import math
import os
from dotenv import load_dotenv


load_dotenv()
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
writer = client.write_api(write_options=SYNCHRONOUS)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", help="Filename of the list of weather station IDs as a comma separated list", required=True)
    parser.add_argument("-s", "--start_year", help="Start year of the scraping (e.g. 2023)", required=True)
    parser.add_argument("-e", "--end_year", help="End year of the scraping (included)", required=True)
    args = parser.parse_args()
    return args.filename, args.start_year, args.end_year


def scrape_and_upload(station_id, start_year, end_year):
    months = [
        '01',
        '02',
        '03',
        '04',
        '05',
        '06',
        '07',
        '08',
        '09',
        '10',
        '11',
        '12'
    ]

    df = pd.DataFrame()
    for y in range(start_year, end_year+1):
        for m in months:
            d = 31
            if m in ['04', '06', '09', '11']:
                d = 30
            elif m == '02':
                d = 28
            res = requests.get(f'https://api.weather.com/v2/pws/history/hourly?stationId={station_id}&format=json&units=m&startDate={y}{m}01&endDate={y}{m}{d}&numericPrecision=decimal&apiKey=e1f10a1e78da46f5b10a1e78da96f525').json()
            df = pd.concat([df, pd.json_normalize(res, record_path=['observations'])], ignore_index=True)
            time.sleep(2)

    try:
        df['timestamp'] = pd.to_datetime(df['obsTimeUtc'])
    except KeyError:
        print(f"{station_id} has no data in the specified date interaval")
        return
    
    df.set_index('timestamp', inplace=True)

    dataPointsTemp = [
        Point(station_id).tag('coords', (lat, lon)).field('T_db[C]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['metric.tempAvg'])
    ]
    dataPointsHum = [
        Point(station_id).tag('coords', (lat, lon)).field('RH[%]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['humidityAvg'])
    ]
    dataPointsWindSpeed = [
        Point(station_id).tag('coords', (lat, lon)).field('v_air[m/s]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['metric.windspeedAvg'] / 3.6)
    ]
    dataPointsWindDir = [
        Point(station_id).tag('coords', (lat, lon)).field('wind_dir[o]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['winddirAvg'])
    ]
    dataPointsDewpt = [
        Point(station_id).tag('coords', (lat, lon)).field('T_dp[C]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['metric.dewptAvg'])
    ]
    dataPointsPressureMin = [
        Point(station_id).tag('coords', (lat, lon)).field('P_atm_min[hPa]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['metric.pressureMin'])
    ]
    dataPointsPressureMax = [
        Point(station_id).tag('coords', (lat, lon)).field('P_atm_max[hPa]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['metric.pressureMax'])
    ]
    if not math.isnan(df['metric.precipTotal'].mean()):
        dataPointsRain = [
            Point(station_id).tag('coords', (lat, lon)).field('rain[mm]', temp).time(time)
                for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['metric.precipTotal'])
        ]
    else:
        dataPointsRain = []
    if not math.isnan(df['metric.precipRate'].mean()):
        dataPointsPrecRate = [
            Point(station_id).tag('coords', (lat, lon)).field('prec_rate[mm/h]', temp).time(time)
                for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['metric.precipRate'])
        ]
    else:
        dataPointsPrecRate = []
    if not math.isnan(df['solarRadiationHigh'].mean()):
        dataPointsRad = [
            Point(station_id).tag('coords', (lat, lon)).field('GHI[W/m2]', temp).time(time)
                for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['solarRadiationHigh'])
        ]
    else:
        dataPointsRad = []
    
    dataPoints = dataPointsTemp + dataPointsHum + dataPointsWindSpeed + dataPointsWindDir + dataPointsDewpt + dataPointsPressureMin + dataPointsPressureMax + dataPointsRain + dataPointsPrecRate + dataPointsRad
    writer.write(bucket="WeatherUnderground", org=INFLUXDB_ORG, record=dataPoints)

    scrape_om_and_upload(station_id, df['lat'].max(), df['lon'].max(), start_year, end_year)


def scrape_om_and_upload(station_id, lat, lon, start_year, end_year):
    df = pd.read_csv(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_year}-01-01&end_date={end_year}-12-31&hourly=temperature_2m,relativehumidity_2m,dewpoint_2m,precipitation,weathercode,pressure_msl,windspeed_10m,winddirection_10m,soil_temperature_0_to_7cm,soil_temperature_7_to_28cm,soil_temperature_28_to_100cm,soil_temperature_100_to_255cm,diffuse_radiation&windspeed_unit=ms&format=csv", header=2)
    df['timestamp'] = pd.to_datetime(df['time'])
    df.set_index('timestamp', inplace=True)
    df['lat'] = lat
    df['lon'] = lon

    dataPointsTemp = [
        Point(station_id).tag('coords', (lat, lon)).field('T_db[C]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['temperature_2m (°C)'])
    ]
    dataPointsHum = [
        Point(station_id).tag('coords', (lat, lon)).field('RH[%]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['relativehumidity_2m (%)'])
    ]
    dataPointsWindSpeed = [
        Point(station_id).tag('coords', (lat, lon)).field('v_air[m/s]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['windspeed_10m (m/s)'])
    ]
    dataPointsWindDir = [
        Point(station_id).tag('coords', (lat, lon)).field('wind_dir[o]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['winddirection_10m (°)'])
    ]
    dataPointsDewpt = [
        Point(station_id).tag('coords', (lat, lon)).field('T_dp[C]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['dewpoint_2m (°C)'])
    ]
    dataPointsPressure = [
        Point(station_id).tag('coords', (lat, lon)).field('P_atm[hPa]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['pressure_msl (hPa)'])
    ]
    dataPointsRain = [
        Point(station_id).tag('coords', (lat, lon)).field('rain[mm]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['precipitation (mm)'])
    ]
    dataPointsWeatherCode = [
        Point(station_id).tag('coords', (lat, lon)).field('weathercode', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['weathercode (wmo code)'])
    ]
    dataPointsRad = [
        Point(station_id).tag('coords', (lat, lon)).field('GHI[W/m2]', temp).time(time)
            for time, lat, lon, temp in zip(df.index, df['lat'], df['lon'], df['diffuse_radiation (W/m²)'])
    ]
    dataPoints = dataPointsTemp + dataPointsHum + dataPointsWindSpeed + dataPointsWindDir + dataPointsDewpt + dataPointsPressure + dataPointsRain + dataPointsWeatherCode + dataPointsRad
    writer.write(bucket="OpenMeteo", org=INFLUXDB_ORG, record=dataPoints)


if __name__ == "__main__":
    filename, start_year, end_year = parse_args()

    try:
        start_year = int(start_year)
        end_year = int(end_year)
    except:
        print("Please enter valid year values")
        exit()

    if start_year > end_year:
        print("Please enter a valid year range (start_year <= end_year)")
        exit()

    with open(filename) as f:
        input = f.read()
        input.strip()
        input.replace(" ", "")
        station_ids = input.split(",")
        for id in station_ids:
            print(f"Scraping data from station {id}...")
            scrape_and_upload(id, start_year, end_year)
        f.close()