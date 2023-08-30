import pandas as pd
import numpy as np
import argparse

def compute_wbt(s):
    """Compute wet-bulb temperature from dry-bulb temperature and relative
    humidity.

    :param s: Series which must contain outdoor drybulb temperature values
        "T_db_o[C]" and relative humidity "RH_o[%]".
    :type s: class:`pandas.core.series.Series` 
    :return: Wet-bulb temperature
    :rtype: float
    """
    t_db = s["T_db_o[C]"]
    rh = s["RH_o[%]"]
    t_wb_o = (
        t_db * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t_db + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * np.sqrt(rh ** 3) * np.arctan(0.023101 * rh)
        - 4.686035
    )
    return t_wb_o

def compute_ttreat_pdec(s, eff):
    """Compute wet-bulb Temperature from dry-bulb temperature and relative
    humidity.

    :param s: Series which must contain at least outdoor drybulb
        temperature values "T_db_o[C]", relative humidity "RH_o[%]" and
        "Date/Time" columns.
    :type s: class:`pandas.core.series.Series` 
    :param timestep: Time resample, defaults to "1H"
    :type timestep: str, optional
    :return: []
    :rtype: []
    """
    t_db = s["T_db_o[C]"]
    t_wb = s["T_wb_o[C]"]
    ttreat = t_db - eff*(t_db - t_wb)
    return ttreat

def cdh_res_pdec(df, thresholds=[18, 21, 24, 26], eff = 0.8):
    """Compute CDH_res considering PDEC technology.

    :param df: DataFrame containing a timestamp index and "T_db_o[C]"
        and "RH_o[%]" columns
    :type df: class:`pandas.core.frame.DataFrame`
    :param threshold: base temperature, defaults to [18, 21, 24, 26]
    :type threshold: List[int], optional
    :param eff: Efficiency of the PDEC system, defaults to 0.8
    :type eff: float, optional
    :return: CDH_res_PDEC
    :rtype: float
    """
    
    df = df.resample("1H").mean(numeric_only=True)

    df["T_wb_o[C]"] = df[["T_db_o[C]", "RH_o[%]"]].apply(compute_wbt, axis=1)
    df["t_treat"] = df[["T_db_o[C]", "T_wb_o[C]"]].apply(compute_ttreat_pdec, args=(eff, ), axis=1)

    my_dict = {}
    for th in thresholds:

        df["dist ttreat-tbase"] = df["t_treat"] - th
        df["dist tamb-tbase"] = df["T_db_o[C]"] - th
        df["dist tamb-ttreat"] = df["t_treat"] - df["T_db_o[C]"]

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
df['RH_o[%]'] = df['RH[%]']
df.index = pd.to_datetime(df['timestamp'])

print("CDH for different temperature setpoints")
print("PDEC: ", cdh_res_pdec(df))
print("Baseline: ", cdh(df))
