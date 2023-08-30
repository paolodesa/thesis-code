import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import exp, sqrt, pi, cos
from datetime import datetime
import argparse

YEAR_DUR = 365*24*3600
DIFFS = {
    'wet_clay': 6.177e-7,
    'dry_clay': 4.891e-7,
    'limestone': 1.907e-7,
    'sand': 4.944e-7,
}
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
DEPTHS = [0.5] + list(range(1, 11))

def estimate_surf_temp_amplitude(df: pd.DataFrame):
    df_mon = df.resample('M').mean(numeric_only=True)
    return 0.5*(df_mon.loc['1970-07-31', 'T_db[C]'] - df_mon.loc['1970-01-31', 'T_db[C]']) + 1.1

def estimate_yearly_mean_surf_temp(df: pd.DataFrame):
    df_year = df.resample('Y').mean(numeric_only=True)
    return df_year.loc['1970-12-31', 'T_db[C]'] + 1.7

def estimate_phase_shift(df: pd.DataFrame):
    max_temp_ts = df['T_db[C]'].idxmax()
    return max_temp_ts.timestamp()

def estimate_phase_const(df: pd.DataFrame):
    min_sol_rad = df['GHI[W/m2]'].idxmin()
    day_min_rad = (min_sol_rad.timestamp()/3600) // 24
    day_min_temp = day_min_rad + 46
    return day_min_temp if day_min_temp <= 364 else day_min_temp - 365

def hadvig_exp(alpha: float, h: float, t: int, surf_temp_amplitude: float, yearly_mean_surf_temp: float, phase_shift: float):
    return yearly_mean_surf_temp + surf_temp_amplitude*exp(-h*sqrt(pi/(alpha*YEAR_DUR)))*cos((2*pi/YEAR_DUR)*(t - phase_shift)-h*sqrt(pi/(YEAR_DUR)))

def labs_exp(alpha_daily: float, h: float, t_days: int, surf_temp_amplitude: float, yearly_mean_surf_temp: float, phase_const: float):
    return yearly_mean_surf_temp - surf_temp_amplitude*exp(-h*sqrt(pi/(365*alpha_daily)))*cos((2*pi/(365))*(t_days-phase_const-(h/2)*sqrt(365/(pi*alpha_daily))))


parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help="Path of the TMY file", required=True)
args = parser.parse_args()

df = pd.read_csv(args.file)
df.index = pd.to_datetime(df['timestamp'])

surf_temp_amplitude = estimate_surf_temp_amplitude(df)
yearly_mean_surf_temp = estimate_yearly_mean_surf_temp(df)
phase_shift = estimate_phase_shift(df)
phase_const = estimate_phase_const(df)

for mat, diff in DIFFS.items():
    plt.figure(figsize=(9, 6))
    for i in range(1, 13):
        ts = datetime(1970, i, 15, 12, 0, 0).timestamp()
        # temps = [hadvig_exp(diff, d, ts, surf_temp_amplitude, yearly_mean_surf_temp, phase_shift) for d in DEPTHS]
        temps = [labs_exp(diff*3600*24, d, (ts/3600)//24, surf_temp_amplitude, yearly_mean_surf_temp, phase_const) for d in DEPTHS]
        depths_hr = np.linspace(0.5, 10, 100)
        # temps_curve = [hadvig_exp(diff, d, ts, surf_temp_amplitude, yearly_mean_surf_temp, phase_shift) for d in depths_hr]
        temps_curve = [labs_exp(diff*3600*24, d, (ts/3600)//24, surf_temp_amplitude, yearly_mean_surf_temp, phase_const) for d in depths_hr]
        plt.plot(temps_curve, depths_hr, zorder=1)
        plt.scatter(temps, DEPTHS, label=MONTHS[i-1], zorder=2)
    plt.xlabel("Temperature [°C]")
    plt.ylabel("Ground depth [m]")
    plt.xticks(range(0, 31, 5))
    plt.yticks(range(0, 11))
    plt.xticks(range(0, 30, 1), minor=True)
    plt.yticks(np.arange(0, 10, 0.5), minor=True)
    plt.tick_params(which='minor', length=0)
    plt.title(mat)
    plt.grid()
    plt.grid(which='minor', alpha=0.3)
    plt.legend()

df_daily = df.resample('D').mean(numeric_only=True)
alpha_daily = 6.177e-7*3600*24
plt.figure(figsize=(9, 6))
for d in range(1, 7):
    df_daily[f'soil_temp_{d}m'] = df_daily.index.map(lambda t: labs_exp(alpha_daily, d, (t.timestamp()/3600)//24, surf_temp_amplitude, yearly_mean_surf_temp, phase_const))
    plt.plot(df_daily.index.map(lambda t: (t.timestamp()/3600)//24), df_daily[f'soil_temp_{d}m'], label=f'{d} meters')
plt.plot(df_daily.index.map(lambda t: (t.timestamp()/3600)//24), df_daily['T_db[C]'], label='Air')
plt.xlabel('Days of the year')
plt.ylabel('Temperature [°C]')
plt.title('Soil surface temperature at various depths (wet clay)')
plt.grid()
plt.legend()
plt.show()