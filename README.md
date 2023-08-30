# Open Source Weather Toolkit

This project uses data scraping to collect weather data from [Weather Underground](https://www.wunderground.com/)'s public stations and store in a local **InfluxDB** instance. This data can then be accesed by several tools, which allow users to conduct many climate-realted analysis. The toolkit was developed during the MSc in *ICT for Smart Societies* at *Politecnico di Torino* as my Master's Thesis.

## Requirements

First of all, all the tools have been written in **Python** (version 3.9 was used during development). Therfore, users need to have it installed on their systems in order to run the code. Additionally, as mentined before, this project stores the scraped data in InfluxDB, thus users will need to setup a [self-hosted](https://docs.influxdata.com/influxdb/v2.7/install/) instance or use a [cloud-hosted](https://www.influxdata.com/products/influxdb-cloud/serverless/) one, provided by InfluxData.\
In oder to installed the required Python packages it is suggested to create a virtual environment and run `pip install -r requirements.txt` in the project root.\
**Before running any code**, two buckets called `WeatherUnderground` and `OpenMeteo` must be created inside InfluxDB (the names can be changed, alongside all their references in the code).

### Environment variables

The file `.env.example` shows an example of the `.env` file where users will need to store the environment variables, required to connect to InfluxDB, which are:
- **INFLUXDB_ORG**: the organization name inside the InfluxDB instance
- **INFLUXDB_TOKEN**: the API token required to interact with the database
- **INFLUXDB_URL**: the full URL of the InfluxDB instance

## How to use the tools

Once the configuration described in the requirements section is reached, all the tools should work as expected.

### Data scraper and uploader

The script `data_scraper_and_uploader.py`, which can be found in the root of the project, **must be executed first** because it will start the scraping process and upload the data to the InfluxDB database, which is then accessed by all the other tools. The script requires the following parameters:
- `-f/--filename`: this is the path of the file which contains a **comma separated list** of the IDs of the weather stations whose data will be scraped (the IDs can be found on Weather Underground's [map](https://www.wunderground.com/wundermap))
- `-s/--start_year`: this is the year the data scraping should start from (e.g. 2023)
- `-e/--end_year`: this is the year the data scraping should end at (included)

**NOTE**: during this process, the coordinates of each weather station will be used to query [Open-Meteo's Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), which combines observations with reanalisys models' outputs, and upload its data to the `OpenMeteo` bucket.
