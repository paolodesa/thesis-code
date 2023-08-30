import pandas as pd
from math import exp, sqrt, pi, cos
import argparse

def estimate_surf_temp_amplitude(df: pd.DataFrame):
    df_mon = df.resample('M').mean(numeric_only=True)
    return 0.5*(df_mon.loc['1970-07-31', 'T_db[C]'] - df_mon.loc['1970-01-31', 'T_db[C]']) + 1.1

def estimate_yearly_mean_surf_temp(df: pd.DataFrame):
    df_year = df.resample('Y').mean(numeric_only=True)
    return df_year.loc['1970-12-31', 'T_db[C]'] + 1.7

def estimate_phase_const(df: pd.DataFrame):
    min_sol_rad = df['GHI[W/m2]'].idxmin()
    day_min_rad = (min_sol_rad.timestamp()/3600) // 24
    day_min_temp = day_min_rad + 46
    return day_min_temp if day_min_temp <= 364 else day_min_temp - 365

def labs_exp_hourly(alpha_hourly: float, h: float, t_hours: int, surf_temp_amplitude: float, yearly_mean_surf_temp: float, phase_const: float):
    return yearly_mean_surf_temp - surf_temp_amplitude*exp(-h*sqrt(pi/(365*24*alpha_hourly)))*cos((2*pi/(365*24))*(t_hours-phase_const-(h/2)*sqrt(365*24/(pi*alpha_hourly))))

def cdh_res_eahx(df, var1, var2, var3, diffus = 6.177*(10**(-7)), depth = 2.5, eff= 0.8, thresholds=[18, 21, 24, 26]):
        """Compute CDH_res considering EAHX technology.

        :param df: DataFrame containing a timestamp index and "T_db_o[C]"
            column
        :type df: class:`pandas.core.frame.DataFrame`
        :param var1: average soil surface temperature
        :type var1: float
        :param var2: amplitude of soil surface temperature
        :type var2: float
        :param var3: phase of soil surface temperature
        :type var3: float
        :param depth: soil depth of EAHX tubes in meters, defaults to 2.5
        :type depth: float, optional
        :param diffus: soil thermal diffusity in m2/s, defaults to 6.177*10^-7 (wet clay)
        :type diffus: float, optional
        :param eff: EAHX efficiency, defaults to 0.8
        :type eff: float, optional
        :param thresholds: base temperature, defaults to [18, 21, 24, 26]
        :type thresholds: List[int], optional
        :return: CDH_res_EAHX
        :rtype: float
        """
        df = df.resample("1H").mean(numeric_only=True)
        
        df["soilT"] = df.index.map(lambda t: labs_exp_hourly(diffus*3600, depth, (t.timestamp()//3600), var2, var1, var3))
        df["t_treat"] = df['T_db_o[C]'] - eff*(df['T_db_o[C]'] - df['soilT'])

        my_dict = {}
        for th in thresholds:

            df["dist ttreat-tbase"] = df["t_treat"] - th
            df["dist tamb-tbase"] = df["T_db_o[C]"] - th
            df["dist tamb-ttreat"] = df["T_db_o[C]"] - df["t_treat"]

            sum_dist =  df["dist ttreat-tbase"].where(df["dist ttreat-tbase"]>0).sum()

            my_dict[str(th)+"°C"] = sum_dist

        return my_dict

def cdh(df, thresholds=[18, 21, 24, 26]):
    """Compute Cooling Degree Hours

    :param df: DataFrame containing a timestamp index and "T_db_o[C]"
        column
    :type df: class:`pandas.core.frame.DataFrame`
    :param thresholds: temperature thresholds from which compute residuals,
        defaults to [18, 21, 24, 26, 28]
    :type thresholds: List[int], optional
    :return: Cooling degree hours
    :rtype: dict
    """
    df = df.resample("1H").mean(numeric_only=True)
    
    my_dict = {}
    for th in thresholds:
        df[str(th)+"°C"] = df["T_db_o[C]"]-th
        sum_dist = df[str(th)+"°C"].where(df[str(th)+"°C"]>0).sum()
        my_dict[str(th)+"°C"] = sum_dist

    return my_dict

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help="Path of the TMY file", required=True)
args = parser.parse_args()

df = pd.read_csv(args.file)
df['T_db_o[C]'] = df['T_db[C]']
df.index = pd.to_datetime(df['timestamp'])
surf_temp_amplitude = estimate_surf_temp_amplitude(df)
yearly_mean_surf_temp = estimate_yearly_mean_surf_temp(df)
phase_const = estimate_phase_const(df)
print("CDH for different temperature setpoints")
print("EAHX: ", cdh_res_eahx(df, yearly_mean_surf_temp, surf_temp_amplitude, phase_const))
print("Baseline: ", cdh(df))