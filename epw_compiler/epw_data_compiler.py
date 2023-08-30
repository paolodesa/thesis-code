import numpy as np
import scipy.stats
import math
import re
import pytz
from tzwhere import tzwhere


def t_dew_point(t_db, rh):
    """Compute dew point temperature according to Meteonorm formula.

    :param t_db: Dry bulb temperature in °C
    :type t_db: float
    :param rh: Relative humidity
    :type rh: float
    :return: Dew point temperature in °C
    :rtype: float
    """
    # needed params are T dry bulb in celsius and Relative Humidity in %
    if rh != 0:
        t_dp = pow((1/(t_db+273.15)-(1.85*pow(10,-4))*math.log(rh/100)),-1) - 273.15
    else:
        t_dp = float("nan")
    return t_dp

def es_td(t_dp):
    """Compute saturated vapour pressure (hPa) at dew point temperature
    according to Meteonorm formula.

    :param t_dp: Dew point temperature in °C
    :type t_dp: float
    :return: Saturated vapour pressure at dew point temperature in hPa
    :rtype: float
    """
    # needed param is T dew point in celsius
    es = 6.11*math.exp(17.1*t_dp/(234.2+t_dp))
    return es


def hiri(es, t_db, kt_d):
    """Compute horizontal infrared radiation intensity (Wh/m2) according to
    Meteonorm formula.

    :param es: [description]
    :type es: [type]
    :param t_db: Dry bulb temperature in °C
    :type t_db: float
    :param kt_d: [description]
    :type kt_d: [type]
    :return: [description]
    :rtype: [type]
    """
    # needed params are saturated vapour pressure at T dew point es, T dry bulb
    # and clearness index kt_d
    SIGMA = 5.67*pow(10,-8) # costante di Boltzmann in W/m2*K4
    return SIGMA*pow((94+12.6*math.log(100*es)-13*kt_d+0.341*(t_db+273.15)),4)


def extra_hor_rad(gh, t, lat, long, dt=2):
    """Compute extraterrestrial solar radiation and clearness index.

    :param gh: [description]
    :type gh: [type]
    :param t: [description]
    :type t: [type]
    :param lat: Latitude in radians
    :type lat: float
    :param long: Longitude in radians
    :type long: float
    :param dt: [description], defaults to 2
    :type dt: int, optional
    :return: Tuple made of (extraterrestrial horizontal radiation, clearness
        index)
    :rtype: tuple
    """
    # TODO: Magari spezzare extra_hor e clearness index.
    # Constant values
    I0 = 1366  # solar radiation intensity in W/m2
    omega0 = 2*math.pi/365.2422

    dy = t.dayofyear
    y = t.year
    h = t.hour
    
    n0 = 78.8946+0.2422*(y-1957)-int((y-1957)/4)
    t1 = -0.5-long/(2*math.pi)-n0
    omegat = omega0*(dy+t1)
    
    # Compute solar time.
    # reference https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time
    b = (360*(dy-81)/365)*math.pi/180 
    eot = 9.87*math.sin(2*b) - 7.53*math.cos(b) -1.5*math.sin(b)  
    time_offset = eot + 4*(long*180/math.pi - dt*15)
    # return time_offset
    st = h + time_offset/60 + 0.5 # solar time: + 0.5 added to center at mid hour
    omegas = ((st-12)*15)*math.pi/180 # hourly angle/ solar time in radians
    
    # compute declination 
    delta = 0.0064979+0.405906*math.sin(omegat)+0.0020054*math.sin(2*omegat) -\
            0.002988*math.sin(3*omegat) - 0.0132296*math.cos(omegat) +\
            0.0063809*math.cos(2*omegat) + 0.0003508*math.cos(3*omegat)
    
    # compute solar altitude (rad)
    hs = math.asin(math.sin(lat)*math.sin(delta)+math.cos(lat)*math.cos(delta)*math.cos(omegas))

    # compute solar azimuth (rad)
    # gamma_s = math.asin(math.cos(delta)*math.sin(omegas)/math.cos(hs))

    # compute correction to actual solar distance at any specific time in the year
    e = 1+ 0.0334*math.cos(dy*2*math.pi/365.25-0.048869)
    
    # Day.
    if hs >= 0:
        # extraterrestrial radiation
        g0 = I0*e*math.sin(hs)
        # compute clearness index corrected for elevation as suggested by meteonorm
        kt_h = gh/g0
        # correction for low elevation
        if hs <= 10:
            kt_h = min(kt_h,0.8)
        
        # old linear method to split diffuse and direct radiation
        # if kt_h <= 0.22:
        #     g_diff = (1-0.09*kt_h)*gh
        # elif kt_h > 0.22 and kt_h <= 0.8:
        #     g_diff = (0.9511-0.1604*kt_h+4.388*pow(kt_h,2)-\
        #               16.638*pow(kt_h,3)+12.336*pow(kt_h,4))*gh
        # elif kt_h >0.8:
        #     g_diff = 0.165*gh
    
    # Night.
    else:
        g0 = 0
        kt_h = 0
        # g_dir = 0
        # g_diff = 0
    
    # g_dir = (gh-g_diff)/mah.sin(hs)       
    
    return g0, kt_h


def brl_model(g0, kt_d, kt_h_list, t, lat, long, dt=2):
    """Boland-Ridley-Lauret model for diffuse/direct radiation split from
    global radiation.

    :param g0: [description]
    :type g0: [type]
    :param kt_d: [description]
    :type kt_d: [type]
    :param kt_h_list: [description]
    :type kt_h_list: [type]
    :param t: [description]
    :type t: [type]
    :param lat: [description]
    :type lat: [type]
    :param long: [description]
    :type long: [type]
    :param dt: [description], defaults to 2
    :type dt: int, optional
    :return: [description]
    :rtype: [type]
    """
    # const
    omega0 = 2*math.pi/365.2422
    
    # daytime
    if g0 != 0:
        
        # compute psi - persistence
        # sunrise
        if kt_h_list[0] == 0 and kt_h_list[1] != 0 and kt_h_list[2] != 0 :
            psi = kt_h_list[2]
        # sunset
        elif kt_h_list[0] != 0 and kt_h_list[1] != 0 and kt_h_list[2] == 0:
            psi = kt_h_list[0]
        # daytime
        else:
            psi = (kt_h_list[0]+kt_h_list[2])/2
        
        dy = t.dayofyear
        y = t.year
        h = t.hour
        
        n0 = 78.8946+0.2422*(y-1957)-int((y-1957)/4)
        t1 = -0.5-long/(2*math.pi)-n0
        omegat = omega0*(dy+t1)
        
        # compute solar angle
        # reference https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time
        b = (360*(dy-81)/365)*math.pi/180 
        eot = 9.87*math.sin(2*b) - 7.53*math.cos(b) -1.5*math.sin(b)  
        time_offset = eot + 4*(long*180/math.pi - dt*15)
        st = h + time_offset/60 + 1/2 # solar time: 0.5 added to center at mid hour
        omegas = ((st-12)*15)*math.pi/180 # hourly angle/ solar time in radians
        
        # compute declination 
        delta = 0.0064979+0.405906*math.sin(omegat)+0.0020054*math.sin(2*omegat) -\
                0.002988*math.sin(3*omegat) - 0.0132296*math.cos(omegat) +\
                0.0063809*math.cos(2*omegat) + 0.0003508*math.cos(3*omegat)
        
        # compute elevation/solar angle
        hs = math.asin(math.sin(lat)*math.sin(delta)+math.cos(lat)*math.cos(delta)*math.cos(omegas))
        hs = hs*180/math.pi
        
        # BRL model generic parameters reference http://dx.doi.org/10.1016/j.rser.2013.08.023
        d = 1/(1 + math.exp(-5.38 + 6.63*kt_h_list[1]+0.006*st-0.007*hs+\
                                  1.75*kt_d+1.31*psi))
        
        # Params specific for Lisbon reference http://dx.doi.org/10.1016/j.rser.2013.08.023
        # d = 1/(1 + math.exp(-5.08 + 6.12*kt_h_list[1]+0.0027*st-0.009*hs+\
        #                           1.40*kt_d+1.51*psi))
        
        # Params for Alps locations reference http://eprints-phd.biblio.unitn.it/1484/1/TESI.pdf
        # d = 1/(1 + math.exp(1.2655 - 6.5092*kt_h_list[1]+0.0849*st-0.0062*hs+\
        #                           2.9967*kt_d+0.6482*psi))
        
        # direct and diffuse split
        g_diff = d*g0
        g_dir = (g0-g_diff) / math.sin(hs*math.pi/180)
        # avoid strange values due to high kt at low elevation angles (no reference)
        g_dir=min(1366, g_dir)
        
        if g_dir < 0:
            g_dir = 0
    
    # nighttime
    else:
        g_dir = 0
        g_diff = 0 
        
    return g_diff,g_dir


def dni_from_ghi(ghi, dif, t, lat, long, dt=2):
    """Compute Direct Normal Irradiation (DNI) from Global Horizontal
    Irradiation (GHI) and Diffuse Horizontal Irradiation (DIF).
    """
    I0 = 1366  # solar radiation intensity in W/m2
    omega0 = 2*math.pi/365.2422

    dy = t.dayofyear
    y = t.year
    h = t.hour
    
    n0 = 78.8946+0.2422*(y-1957)-int((y-1957)/4)
    t1 = -0.5-long/(2*math.pi)-n0
    omegat = omega0*(dy+t1)
    
    # Compute solar time.
    # reference https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time
    b = (360*(dy-81)/365)*math.pi/180 
    eot = 9.87*math.sin(2*b) - 7.53*math.cos(b) -1.5*math.sin(b)  
    time_offset = eot + 4*(long*180/math.pi - dt*15)
    # return time_offset
    st = h + time_offset/60 + 0.5 # solar time: + 0.5 added to center at mid hour
    omegas = ((st-12)*15)*math.pi/180 # hourly angle/ solar time in radians
    
    # compute declination 
    delta = 0.0064979+0.405906*math.sin(omegat)+0.0020054*math.sin(2*omegat) -\
            0.002988*math.sin(3*omegat) - 0.0132296*math.cos(omegat) +\
            0.0063809*math.cos(2*omegat) + 0.0003508*math.cos(3*omegat)
    
    # compute solar altitude (rad)
    hs = math.asin(math.sin(lat)*math.sin(delta)+math.cos(lat)*math.cos(delta)*math.cos(omegas))

    # compute solar azimuth (rad)
    # gamma_s = math.asin(math.cos(delta)*math.sin(omegas)/math.cos(hs))

    # compute correction to actual solar distance at any specific time in the year
    e = 1+ 0.0334*math.cos(dy*2*math.pi/365.25-0.048869)
    
    # Day.
    if hs >= 0:

        # direct and diffuse split
        g_dir = (ghi-dif)/math.sin(hs) 
    
    # Night.
    else:
        g_dir = 0
     
    return g_dir


def mode_zero(x):
    """Compute mode but exclude value 0 if other numbers are present.
    Example:
    mode_zero([0, 0, 1, 2, 1, 0, 0]) -> 1
    mode_zero([0, 0, 0, 0]) -> 0

    :param x: List of int numbers
    :type x: list
    :return: Mode value
    :rtype: int
    """
    mode_array = scipy.stats.mode(x[x!=0], keepdims=True)[0]
    if len(mode_array) == 0:
        return 0
    elif np.isnan(mode_array):
        return 0
    else:
        return mode_array[0]
    
def mode_std(x):
    """Compute mode but exclude value 0 if other numbers are present.
    Example:
    mode_zero([0, 0, 1, 2, 1, 0, 0]) -> 1
    mode_zero([0, 0, 0, 0]) -> 0

    :param x: List of int numbers
    :type x: list
    :return: Mode value
    :rtype: int
    """
    mode_array = scipy.stats.mode(x, keepdims=True)[0]
    if len(mode_array) == 0:
        return np.nan
    elif np.isnan(mode_array):
        return np.nan
    else:
        return mode_array[0]

def compile_weather_data(df, lon, lat):
    """Create and fill weather data columns in the dataframe.

    :param csv_path: Path to CSV file
    :type csv_path: `str` or `Path`
    :param lon: Longitude in radians
    :type lon: float
    :param lat: Latitude in radians
    :type lat: float
    :return: Dataframe with new columns
    :rtype: class:`pandas.core.frame.DataFrame`
    """
    # col_names = [
    #     "v_air[m/s]",
    #     "wind_dir[o]",
    #     "T_db[C]",
    #     "RH[%]",
    #     "abs_humidity[g/m3]",
    #     "P_atm[hPa]",
    #     "bright_N",
    #     "bright_E",
    #     "bright_S",
    #     "bright_O",
    #     "rain[mm]",
    #     "rain_type[int]",
    #     "GHI[W/m2]",
    # ]

    weather_df = df
    
    bright_cols = [col for col in weather_df.columns if "bright" in col.lower()]
    resample_dict = {
        "v_air[m/s]": "mean",
        "wind_dir[o]": lambda x: mode_std(x),
        "T_db[C]": "mean",
        "RH[%]": "mean",
        "abs_humidity[g/m3]": "mean",
        "P_atm[hPa]": "mean",
        "rain[mm]": "sum",
        "rain_type[int]": lambda x: mode_zero(x),
        "GHI[W/m2]": "mean"
    }
    for bc in bright_cols:
        resample_dict.update({bc: "mean"})

    # Resample to hourly values.
    weather_df = weather_df.resample("1H").agg(resample_dict)
    
    for i in range(len(weather_df)):
        if np.isnan(weather_df["GHI[W/m2]"].iloc[i]):
            hour = weather_df.index[i].hour
            start = max(i-72, 0)
            end = min(i+73, len(weather_df))
            temp_df = weather_df.iloc[start:end]
            new_val = np.nanmean(temp_df[temp_df.index.hour==hour].loc[:, "GHI[W/m2]"])
            weather_df["GHI[W/m2]"].iloc[i] = new_val
            # mean_ghi = [el for el in weather_df["GHI[W/m2]"] if weather_df.index.hour == ]
   
    # TODO its not best method for wind_dir
    weather_df = weather_df.interpolate(method="linear")
    weather_df["wind_dir[o]"] = [(n+22.5)//45*45 for n in weather_df["wind_dir[o]"]]   

    # Dew point temperature [°C].
    if "T_dp[C]" not in weather_df.columns:
        t_dp = [
            t_dew_point(
                float(weather_df["T_db[C]"].iloc[i]),
                float(weather_df["RH[%]"].iloc[i]),
            )
            for i in range(0, len(weather_df))
        ]
        weather_df["T_dp[C]"] = t_dp

    # Saturated vapour pressure [hPa] at dew point temperature.
    if "es[hPa]" not in weather_df.columns:
        es = [
            es_td(float(weather_df["T_dp[C]"].iloc[i]))
            for i in range(0, len(weather_df))
        ]
        weather_df["es[hPa]"] = es

    # extraterrestrial radiation and kt
    g0_list = []
    kt_h_list = []
    for i in range (0,len(weather_df)):
        g0, kt = extra_hor_rad(float(weather_df["GHI[W/m2]"].iloc[i]),\
                weather_df.index[i],lat,lon)
  
        g0_list.append(g0)
        kt_h_list.append(kt)
    weather_df["extra_computed"] = g0_list
    weather_df["kt_h"] = kt_h_list
    kt_d_df = weather_df["GHI[W/m2]"].resample("1D").sum()/weather_df["extra_computed"].resample("1D").sum()

    # add incoming longwave horizontal radiation (horizontal infrared radiation inensity) (Wh/m2)
    infrared = [hiri(float(weather_df["es[hPa]"].iloc[i]),float(weather_df["T_db[C]"].iloc[i]),\
                float(kt_d_df.loc[weather_df.index[i].replace(hour=0, minute=0, second=0)])) for i in range (0,len(weather_df))]
    weather_df["HIRI[W/m2]"] = infrared

    # add diffuse/direct radiation
    if "DIF[W/m2]" and "DNI[W/m2]" not in weather_df.columns:
        diffuse = []
        direct = []
    
        # Compute DT timezone for every datetime.
        timezone = get_timezone(lat, lon)
        weather_df["dt"] = weather_df.index
        weather_df["dt"] = weather_df["dt"].apply(get_dt, args=(timezone, ))
    
        # Apply model.
        for i in range (1,len(weather_df)-1):
            g_diff, g_dir = brl_model(float(weather_df["GHI[W/m2]"].iloc[i]),\
                            float(kt_d_df.loc[weather_df.index[i].replace(hour=0,\
                            minute=0, second=0)]), [float(weather_df["kt_h"].iloc[i-1]),\
                            float(weather_df["kt_h"].iloc[i]),float(weather_df["kt_h"].iloc[i+1])],\
                            weather_df.index[i], lat, lon, weather_df["dt"].iloc[i])
            diffuse.append(g_diff)
            direct.append(g_dir)
        diffuse = [np.nan] + diffuse + [np.nan]
        direct = [np.nan] + direct + [np.nan]
        weather_df["DIF[W/m2]"] = diffuse
        weather_df["DNI[W/m2]"] = direct

    # Present weather observation field,
    weather_df["present_weather_observation"] = weather_df["rain[mm]"]
    weather_df.loc[weather_df["rain[mm]"] == 0, "present_weather_observation"] = 9
    weather_df.loc[weather_df["rain[mm]"] != 0, "present_weather_observation"] = 0
    weather_df.loc[weather_df["rain_type[int]"] == 40, "present_weather_observation"] = 9

    # Present weather codes field,
    weather_df["present_weather_codes"] = weather_df["present_weather_observation"]
    weather_df.loc[weather_df["present_weather_observation"] == 9, "present_weather_codes"] = 999999999
    weather_df.loc[weather_df["rain_type[int]"] == 51, "present_weather_codes"] = 993999999
    weather_df.loc[weather_df["rain_type[int]"] == 52, "present_weather_codes"] = 994999999
    weather_df.loc[weather_df["rain_type[int]"] == 53, "present_weather_codes"] = 995999999
    weather_df.loc[weather_df["rain_type[int]"] == 61, "present_weather_codes"] = 909999999
    weather_df.loc[weather_df["rain_type[int]"] == 62, "present_weather_codes"] = 919999999
    weather_df.loc[weather_df["rain_type[int]"] == 63, "present_weather_codes"] = 929999999
    weather_df.loc[weather_df["rain_type[int]"] == 67, "present_weather_codes"] = 909099999
    weather_df.loc[weather_df["rain_type[int]"] == 68, "present_weather_codes"] = 919199999
    weather_df.loc[weather_df["rain_type[int]"] == 70, "present_weather_codes"] = 999099999
    weather_df.loc[weather_df["rain_type[int]"] == 71, "present_weather_codes"] = 999099999
    weather_df.loc[weather_df["rain_type[int]"] == 72, "present_weather_codes"] = 999199999
    weather_df.loc[weather_df["rain_type[int]"] == 73, "present_weather_codes"] = 999299999
    weather_df.loc[weather_df["rain_type[int]"] == 74, "present_weather_codes"] = 999699999
    weather_df.loc[weather_df["rain_type[int]"] == 89, "present_weather_codes"] = 999994999

    return weather_df

def get_timezone(lat, lon):
    zone = tzwhere.tzwhere()
    return zone.tzNameAt(lat, lon)

def get_dt(date, timezone):
    obj = pytz.timezone(timezone).localize(date).strftime("%z")
    dt = re.compile(r'(?:)(-?\+?\d+)(00)(?:)').match(obj).group(1)
    return int(dt)

def compile_epw_data(df, lat, lon):
    return compile_weather_data(df=df, lon=lon, lat=lat)
    # w_df.to_csv(
    #     end_filename,
    #     sep=';',
    #     date_format="%Y-%m-%d %H:%M:%S"
    # )
