import argparse
import math
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--id", help="Weather station ID", required=True)
    parser.add_argument("-y", "--year", help="Year", type=int, required=True)
    args = parser.parse_args()
    return args.id.upper(), args.year


def abs_humidity_from_T_and_rh(T, rh):
    # This formula includes an expression for saturation vapor pressure (Bolton 1980) accurate to 0.1% over the temperature range -30°C≤T≤35°C
    return (6.112 * pow(math.e, (17.67 * T) / (T + 243.5)) * rh * 18.02) / ((273.15 + T) * 100 * 0.08314)


def compute_rain_type(prec_total, prec_rate):
    if prec_total == 0.0:
        return 40
    elif prec_rate < 0.5:
        return 51
    elif prec_rate <= 1.0:
        return 53
    elif prec_rate <= 2.5:
        return 61
    else:
        return 63


def clean_data(df, year):
    df = df.resample("1H").mean(numeric_only=True)
    df.index = df.index.tz_localize(None)

    # Set the desired time range
    start_date = f'{year}-01-01 00:00:00'
    end_date = f'{year}-12-31 23:59:59'

    # Create a DateTimeIndex with hourly frequency
    hourly_range = pd.date_range(start=start_date, end=end_date, freq='H')

    # Create an empty DataFrame with the DateTimeIndex
    df_filled = pd.DataFrame(index=hourly_range)

    # Merge the empty DataFrame with your original data
    df_merged = df_filled.merge(df, left_index=True, right_index=True, how='left')

    # Forward-fill missing values with previous value at the same hour
    df_filled = df_merged.groupby([df_merged.index.hour]).ffill()

    # Backward-fill remaining missing values
    df = df_filled.groupby([df_merged.index.hour]).bfill()

    df_clean = pd.DataFrame(
        {
            "v_air[m/s]": df['v_air[m/s]'],
            "wind_dir[o]": df['wind_dir[o]'],
            "T_db[C]": df['T_db[C]'],
            "T_dp[C]": df['T_dp[C]'],
            "RH[%]": df['RH[%]'],
            "abs_humidity[g/m3]": [abs_humidity_from_T_and_rh(T, rh) for T, rh in zip(df['T_db[C]'], df['RH[%]'])],
            "P_atm[hPa]": [(pressureMin+presureMax)/2 for pressureMin, presureMax in zip(df['P_atm_min[hPa]'], df['P_atm_max[hPa]'])],
            "rain[mm]": df['rain[mm]'],
            "rain_type[int]": [compute_rain_type(prec_total, prec_rate) for prec_total, prec_rate in zip(df['rain[mm]'], df['prec_rate[mm/h]'])],
            "GHI[W/m2]": df['GHI[W/m2]']
        },
        index=df.index
    )
    return df_clean
