import argparse
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14


parser = argparse.ArgumentParser()
parser.add_argument("--lat", help="Latitude", type=float, required=True)
parser.add_argument("--lon", help="Longiture", type=float, required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year (included)", type=int, required=True)
args = parser.parse_args()

lat, lon, start_year, end_year = args.lat, args.lon, args.start_year, args.end_year
    
df = pd.read_csv(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_year}-01-01&end_date={end_year}-12-31&daily=temperature_2m_mean&timezone=GMT&format=csv", header=2)
df['timestamp'] = pd.to_datetime(df['time'])
df.set_index('timestamp', inplace=True)
df = df.resample('Y').mean(numeric_only=True)

years = range(start_year, end_year+1)

fig = plt.figure(figsize=(16, 9))
plt.plot(years, df['temperature_2m_mean (°C)'])
plt.xlabel('Year')
plt.ylabel('Mean dry-bulb air temperature [°C]')
plt.show()