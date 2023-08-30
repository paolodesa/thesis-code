import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


parser = argparse.ArgumentParser()
parser.add_argument("--id", help="Weather station ID", required=True)
parser.add_argument("--start_year", help="Start year", type=int, required=True)
parser.add_argument("--end_year", help="End year", type=int, required=True)
args = parser.parse_args()

station_id, start_year, end_year = args.id.upper(), args.start_year, args.end_year


def hdh(df, thresholds=[18, 20, 22]):
        """Compute Heating Degree Hours

        :param df: DataFrame containing at least "timestamp" and "T_db_o[C]"
            columns
        :type df: class:`pandas.core.frame.DataFrame`
        :param thresholds: temperature thresholds from which compute residuals,
            defaults to [18, 20, 22]
        :type thresholds: list, optional
        :return: Heating degree hour
        :rtype: dict
        """
        df = df.set_index("timestamp")
        df = df.resample("1H").mean()
        
        my_dict = {}
        for th in thresholds:
            df["dist_"+str(th)] = th - df["T_db_o[C]"]
            sum_dist = df["dist_"+str(th)].where(df["dist_"+str(th)]>0).sum()
            my_dict["dist_"+str(th)] = sum_dist

        return my_dict


def cdh(df, thresholds=[18, 21, 24, 26, 28]):
        """Compute Cooling Degree Hours

        :param df: DataFrame containing at least "timestamp" and "T_db_o[C]"
            columns
        :type df: class:`pandas.core.frame.DataFrame`
        :param thresholds: temperature thresholds from which compute residuals,
            defaults to [18, 21, 24, 26, 28]
        :type thresholds: list, optional
        :return: Cooling degree hour
        :rtype: dict
        """
        df = df.set_index("timestamp")
        df = df.resample("1H").mean()
        
        my_dict = {}
        for th in thresholds:
            df["dist_"+str(th)] = df["T_db_o[C]"]-th
            sum_dist = df["dist_"+str(th)].where(df["dist_"+str(th)]>0).sum()
            my_dict["dist_"+str(th)] = sum_dist

        return my_dict


df_t = pd.read_csv(f'{station_id}_ISO_TMY_WeatherUnderground_{start_year}_{end_year}.csv')
df_t["timestamp"] = pd.to_datetime(df_t["timestamp"])
df_t['T_db_o[C]'] = df_t["T_db[C]"]
df_mt = pd.read_csv(f'{station_id}_mean_TMY_WeatherUnderground_{start_year}_{end_year}.csv')
df_mt["timestamp"] = pd.to_datetime(df_mt["timestamp"])
df_mt['T_db_o[C]'] = df_mt["T_db[C]"]

df_t_om = pd.read_csv(f'{station_id}_ISO_TMY_OpenMeteo_{start_year}_{end_year}.csv')
df_t_om["timestamp"] = pd.to_datetime(df_t_om["timestamp"])
df_t_om['T_db_o[C]'] = df_t_om["T_db[C]"]
df_mt_om = pd.read_csv(f'{station_id}_mean_TMY_OpenMeteo_{start_year}_{end_year}.csv')
df_mt_om["timestamp"] = pd.to_datetime(df_mt_om["timestamp"])
df_mt_om['T_db_o[C]'] = df_mt_om["T_db[C]"]

hdh_t = hdh(df_t)
hdh_mt = hdh(df_mt)
hdh_t_om = hdh(df_t_om)
hdh_mt_om = hdh(df_mt_om)

cdh_t = cdh(df_t)
cdh_mt = cdh(df_mt)
cdh_t_om = cdh(df_t_om)
cdh_mt_om = cdh(df_mt_om)

x_pos_hdh = np.arange(len(hdh_t.keys()))
width = 0.2

plt.figure()
plt.bar(x_pos_hdh - (width*1.5), hdh_t.values(), width, align='center', label='WU - UNI EN ISO 15927-04:2005')
plt.bar(x_pos_hdh - (width/2), hdh_t_om.values(), width, align='center', label='OM - UNI EN ISO 15927-04:2005')
plt.bar(x_pos_hdh + (width/2), hdh_mt.values(), width, align='center', label='WU - Mean')
plt.bar(x_pos_hdh + (width*1.5), hdh_mt_om.values(), width, align='center', label='OM - Mean')
plt.xticks(x_pos_hdh, [18, 20, 22])
plt.xlabel('Threshold [°C]')
plt.ylabel('HDH')
plt.title(f'HDH for station {station_id} using TMY data')
plt.legend()

x_pos_cdh = np.arange(len(cdh_t.keys()))

plt.figure()
plt.bar(x_pos_cdh - (width*1.5), cdh_t.values(), width, align='center', label='WU - UNI EN ISO 15927-04:2005')
plt.bar(x_pos_cdh - (width/2), cdh_t_om.values(), width, align='center', label='OM - UNI EN ISO 15927-04:2005')
plt.bar(x_pos_cdh + (width/2), cdh_mt.values(), width, align='center', label='WU - Mean')
plt.bar(x_pos_cdh + (width*1.5), cdh_mt_om.values(), width, align='center', label='OM - Mean')
plt.xticks(x_pos_cdh, [18, 21, 24, 26, 28])
plt.xlabel('Threshold [°C]')
plt.ylabel('CDH')
plt.title(f'CDH for station {station_id} using TMY data')
plt.legend()

plt.show()