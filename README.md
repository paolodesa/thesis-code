# Open Source Weather Toolkit

This project uses data scraping to collect weather data from [Weather Underground](https://www.wunderground.com/)'s public stations and store in a local **InfluxDB** instance. This data can then be accesed by several tools, which allow users to conduct many climate-realted analysis. The toolkit was developed during the MSc in *ICT for Smart Societies* at *Politecnico di Torino* as my Master's Thesis.

## Requirements

First of all, all the tools have been written in **Python** (version 3.9 was used during development). Therfore, users need to have it installed on their systems in order to run the code. Additionally, as mentined before, this project stores the scraped data in InfluxDB, thus users will need to setup a [self-hosted](https://docs.influxdata.com/influxdb/v2.7/install/) instance or use a [cloud-hosted](https://www.influxdata.com/products/influxdb-cloud/serverless/) one, provided by InfluxData.\
In oder to installed the required Python packages it is suggested to create a virtual environment and run `pip install -r requirements.txt` in the project root.

### Environment variables

The file `.env.example` shows an example of the `.env` file where users will need to store the environment variables, required to connect to InfluxDB and Mapbox, which are:
- **INFLUXDB_ORG**: the organization name inside the InfluxDB instance
- **INFLUXDB_TOKEN**: the API token required to interact with the database
- **INFLUXDB_URL**: the full URL of the InfluxDB instance
- **MAPBOX_TOKEN**: the public API token required to load the map from Mapbox (it can be obtained with a free account)
- **WEATHER_UNDERGROUND_BUCKET_NAME**: the (unique) name of the InfluxDB bucket where Weather Underground's data will be stored (it is suggested to create 1 bucket per city/area)
- **OPEN_METEO_BUCKET_NAME**: the (unique) name of the InfluxDB bucket where Open Meteo's data will be stored (it is suggested to create 1 bucket per city/area)

## How to use the tools

Once the configuration described in the requirements section is reached, all the tools should work as expected.

### Data scraping and uploading to InfluxDB

The script `data_scraper_and_uploader.py`, which can be found in the root of the project, **must be executed first** because it will start the scraping process and upload the data to the InfluxDB database, which is then accessed by all the other tools. The script requires the following parameters:
- `-f/--filename`: this is the path of the file which contains a **comma separated list** of the IDs of the weather stations whose data will be scraped (the IDs can be found on Weather Underground's [map](https://www.wunderground.com/wundermap))
- `-s/--start_year`: this is the year the data scraping should start from (e.g. 2023)
- `-e/--end_year`: this is the year the data scraping should end at (included)

**NOTE**: during this process, the coordinates of each weather station will be used to query [Open-Meteo's Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), which combines observations with reanalisys models' outputs, and upload its data to the `OpenMeteo` bucket.

### EPW compilation

Inside the `epw_compiler` folder, users can find all the modules necessary to produce an **Energy Plus Weather (EPW)** file (complete of the header), using data from Weather Underground's stations. Users who intend to generate an EPW file should only interact with the `generate_epw.py` script. The following arguments are used as input:
- `--id`: the ID of the weather station to be used as source
- `--year`: the year for which the EPW file should be generated
- `--city`: the city where the weather station is located
- `--country`: the country code (e.g. ITA) of the country where the station is located
- `--state`: the state/province/region where the station is located (optional)
- `--source`: a user-defined description of the data source (optional)
- `--leap`: add this flag to mark the year of the EPW as a leap year
- `--dst_start_date`: the start date (M/D format) of the daylight saving time (optional)
- `--dst_end_date`: the end date (M/D format) of the daylight saving time (optional)
- `--start_weekday`: the start day of the week (optional, default = Monday)
- `--comment1`: first line of comments to be added to the EPW header (optional)
- `--comment2`: second line of comments to be added to the EPW header (optional)

### TMY compilation

Inside the `tmy_compiler` folder, users can find several scripts. The `generate_iso_tmy.py` and `generate_mean_tmy.py` files are used to produce the typical meteorological year (TMY) files, using the *UNI EN ISO 15927-04:2005* norm and a simple hourly averaging over the reference period respectively. Both scripts require the following parameters as input:
- `--id`: the ID of the weather station to be used as source
- `--start_year`: the start year of the weather data which will be used to produce the TMY file
- `--end_year`: the end year of the weather data which will be used to produce the TMY file (included)

**NOTE**: users are recommended to use as source a weather station with an appropriately long data history (10+ years)

Addionally, users can find the `compare_tmy_generation_sources.py` and `compare_tmy_generation_methodods.py` scripts, which produce comparison plots between the TMY files generated using the two different sources (Weather Underground and Open Meteo) and the two different methods (ISO norm and simple averaging) respectively. Both scripts require the following parameters as input:
- `--id`: the ID of the weather station used to generate the TMY files
- `--start_year`: the start year of the weather data which was used to produce the TMY file
- `--end_year`: the end year of the weather data which was used to produce the TMY file (included)

**NOTE**: these scripts read the TMY files, assuming that they are in the same directory where the scripts are executed and they have not been renamed

In order to be able to generate TMY files for past year periods, for which data is not available from Weather Underground, users can find a different version of the `generate_iso_tmy.py` and `generate_mean_tmy.py` scripts inside the `open_meteo` subfolder. Instead of taking a station ID to reference a point on Earth, users will need to input its coordinates. The input parameters are:
- `--lat`: the latitude (in decimal degrees) of the data source point
- `--lon`: the longitude (in decimal degrees) of the data source point
- `--start_year`: the start year of the weather data used to produce the TMY file
- `--end_year`: the end year of the weather data used to produce the TMY file (included)
- `--epw`: add this flag to output the TMY file also in EPW format

in case the `--epw` flag is set, the script also accepts the following inputs:
- `--city`: the city where the source point is located
- `--country`: the country code (e.g. ITA) of the country where the source point is located
- `--state`: the state/province/region where the source point is located (optional)
- `--source`: a user-defined description of the data source (optional)
- `--leap`: add this flag to mark the year of the EPW as a leap year
- `--dst_start_date`: the start date (M/D format) of the daylight saving time (optional)
- `--dst_end_date`: the end date (M/D format) of the daylight saving time (optional)
- `--start_weekday`: the start day of the week (optional, default = Monday)
- `--comment1`: first line of comments to be added to the EPW header (optional)
- `--comment2`: second line of comments to be added to the EPW header (optional)

**NOTE**: all TMY files have their timestamps referenced to the year 1970 as convention

Finally, the script `compare_tmy_periods.py` in the `open_meteo` subfolder allows to plot the comparison of the daily mean dry-bulb air temperature for TMY files referencing different periods. It takes as input:
- `--files`: space separated filenames of the TMY to be compared (in csv format)

**NOTE**: the script assumes that the TMY filenames scructure has not been modified

### UHI effect analysis

Inside the `uhi_effect` folder, users can find the `uhi_map.py` script, which will load a map showing a color-coded representation of the mean daily temperatures registered by all the weather stations. It requires the following inputs:
- `--start_ts`: the full timestamp (ISO 8601 format, e.g. 2023-01-01T00:00:00Z) of the start date for the day selection slider on the map
- `--start_ts`: the full timestamp (ISO 8601 format, e.g. 2023-01-31T00:00:00Z) of the end date for the day selection slider on the map

**NOTE**: avoid selecting too long periods, as the slider may become diffcult to operate

Moreover, users can obtain plots of the temperture gap between the urban area and the sub-urban one with the `compare_temps_by_radius.py` script, which requires the following parameters:
- `--radius`: the radius (in km) of the urban area
- `--lat`: the latitude (in decimal degrees) of the center point of the urban area
- `--lon`: the longitude (in decimal degrees) of the center point of the urban area
- `--start_year`: the start year of the data used for the analysis
- `--end_year`: the end year of the data used for the analysis (included)

**NOTE**: both scripts will use all weather stations present in the InfluxDB's bucket whose name is specified by the `WEATHER_UNDERGROUND_BUCKET_NAME` environment variable; therfore, it was suggested to create 1 bucket per city/area during the setup phase

### EAHX and PDEC cooling systems assessment

First of all, in the `soil_temp_and_cooling_systems` folder, user can find a script to plot the trend of the soil temperature throughout the year. Knowing how the soil temperature varies is useful to understand the principle behind earth-to-air heat exchangers (EAHX), whose cooling potential in a specific location can be evaluted using the `compute_eahx_cdh_res.py` script. A similar analysis can be conducted for a different passive cooling system, namely the passive downdraught evaporative cooling (PDEC) system, with the script `compute_pdec_cdh_res.py`. All three script require only a parameter:
- `-f/-file`: the full path of the TMY file to be used for the assessment

### Climate change analysis

The folder `climate_change` contains 3 scripts which can be used to plot trends of temperature, cooling degree days (CDD) and heating degree days (HDD) over multiple years for a specific weather station. All of them require as input:
- `--id`: the ID of the weather station to be used as source
- `--start_year`: the start year of the analysis
- `--end_year`: the end year of the analysis (included)

In addition, the `open_meteo_long_hist` subfolder contains the same 3 scripts but, using data from the Open Meteo API instead of Weather Underground's stations, in order to be able to have a much longer data history. The inputs to these scripts are:
- `--lat`: the latitude (in decimal degrees) of the data source point
- `--lon`: the longitude (in decimal degrees) of the data source point
- `--start_year`: the start year of the analysis
- `--end_year`: the end year of the analysis (included)

### Comparison of Weather Underground's station data with arbitrary EPW

The script `compare_epw_to_ws.py` was developed to compare the temperature readings of a self-hosted weather station (contained in an EPW file) to the data gathered from a weather station in Weather Underground's network (e.g. the closest one). It requires as input:
- `--id`: the ID of the weather station to be used for comparison
- `--filename`: the filename of the EPW to be used for comparison