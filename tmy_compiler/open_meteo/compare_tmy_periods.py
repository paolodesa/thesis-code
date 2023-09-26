import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14

parser = argparse.ArgumentParser()
parser.add_argument("--files", help="Space separated filenames of the TMY files to be compared", nargs='+', required=True)
args = parser.parse_args()

tmy_files = args.files

fig, ax = plt.subplots(figsize=(16, 9))

for f in tmy_files:
    df = pd.read_csv(f)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df = df.resample('D').mean()
    df = df.interpolate(method='linear')

    label = f.split('_')[-2] + '-' + f.split('_')[-1].split('.')[0]
    plt.plot(df.index, df['T_db[C]'], label=label)

plt.xlabel('Timestamp')
plt.ylabel('Mean daily temperature [°C]')
plt.title(f'Comparison of TMY for different year periods')
plt.legend()
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b, %d'))
plt.show()