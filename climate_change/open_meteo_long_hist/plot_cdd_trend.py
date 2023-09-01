import argparse
import pandas as pd
import matplotlib.pyplot as plt


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
df = df.resample('1D').mean(numeric_only=True)
df = df[~((df.index.month == 2) & (df.index.day == 29))]
df['T_db_o[C]'] = df['temperature_2m_mean (°C)']

cdds = []
years = range(start_year, end_year+1)
for y in years:
    cdds.append(cdd(df[df.index.year == y]))

plt.plot(years, cdds)
plt.xlabel("Year")
plt.ylabel("CDD")
plt.show()