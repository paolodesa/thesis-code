from bs4 import BeautifulSoup
import requests
import re
import json

CONTINENTS = [
    "Asia",
    "North America",
    "Latin America",
    "Australia and Oceania",
    "Europe",
    "Africa",
    "Antarctica"
]

db = {}

with open("ashrae_wmo_db.csv", "w+") as f:
    header = "continent;country;region;city;lat;lon;wmo\n"
    f.write(header)
    for continent in CONTINENTS:
        res = requests.get(
            f"http://ashrae-meteo.info/v2.0/places.php?continent={continent}")
        soup = BeautifulSoup(res.text, "lxml")

        countries = {}

        if (continent != "North America"):
            countries_cont = soup.find_all(class_="ui-accordion-header")
            for country_cont in countries_cont:
                country = country_cont.string
                cities = {}
                for child in country_cont.next_sibling.children:
                    if (child.name == "a"):
                        city = child.string
                        lat = re.search(r'(?<=lat=)-?\d+(\.\d+)?',
                                        child["href"]).group()
                        lon = re.search(r'(?<=lng=)-?\d+(\.\d+)?',
                                        child["href"]).group()
                        wmo = re.search(r'(?<=wmo=).{6}', child["href"]).group()
                        cities[city] = {
                            "lat": lat,
                            "lon": lon,
                            "wmo": wmo
                        }
                        f.write(f"{continent};{country};;{city};{lat};{lon};{wmo}\n")
                countries[country] = cities
        else:
            countries_cont = soup.find_all(id=["ui-id-1", "ui-id-2"])
            for country_cont in countries_cont:
                country = country_cont.string
                regions = {}
                for index, region_cont in enumerate(country_cont.next_sibling.children):
                    if index % 2 == 0:
                        region = region_cont.string
                    else:
                        cities = {}
                        for child in region_cont.children:
                            if (child.name == "a"):
                                city = child.string
                                lat = re.search(r'(?<=lat=)-?\d+(\.\d+)?',
                                                child["href"]).group()
                                lon = re.search(r'(?<=lng=)-?\d+(\.\d+)?',
                                                child["href"]).group()
                                wmo = re.search(r'(?<=wmo=).{6}', child["href"]).group()
                                cities[city] = {
                                    "lat": lat,
                                    "lon": lon,
                                    "wmo": wmo
                                }
                                f.write(f"{continent};{country};{region};{city};{lat};{lon};{wmo}\n")
                        regions[region] = cities
                countries[country] = regions
                    
        db[continent] = countries
    f.close()

with open("ashrae_wmo_db.json", "w+") as f:
    json.dump(db, f, indent=2)
    f.close()
