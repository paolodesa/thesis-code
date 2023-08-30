import argparse
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14

parser = argparse.ArgumentParser()
parser.add_argument("--id", help="Weather station ID", required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year", type=int, required=True)
args = parser.parse_args()

station_id, start_year, end_year = args.id.upper(), args.start_year, args.end_year

mt = pd.read_csv(f'{station_id}_mean_TMY_WeatherUnderground_{start_year}_{end_year}.csv')
t = pd.read_csv(f'{station_id}_ISO_TMY_WeatherUnderground_{start_year}_{end_year}.csv')

mt['timestamp'] = pd.to_datetime(mt['timestamp'])
t['timestamp'] = pd.to_datetime(mt['timestamp'])

mt.set_index('timestamp', inplace=True)
t.set_index('timestamp', inplace=True)

mt = mt.resample('D').mean()
mt = mt.interpolate(method='linear')
t = t.resample('D').mean()
t = t.interpolate(method='linear')

fig = plt.figure(figsize=(16, 9))
plt.plot(mt.index, mt['T_db[C]'], label='Mean over all years')
plt.plot(t.index, t['T_db[C]'], label='Conventional TMY')
plt.xlabel('Timestamp')
plt.ylabel('Mean daily temperature [°C]')
plt.title(f'Comparison between avergaing over all years ({start_year}-{end_year}) of data and conventional TMY construction')
plt.legend()
plt.show()