from influxdb_client import InfluxDBClient
from datetime import timedelta

from dash import Dash, dcc, html, Input, Output, State
import plotly.express as px

import pandas as pd
import ast
import argparse
import os
from dotenv import load_dotenv


load_dotenv()
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN')

parser = argparse.ArgumentParser()
parser.add_argument("--start_ts", help="Start timestamp (e.g. 2023-01-01T00:00:00Z)", required=True)
parser.add_argument("--end_ts", help="End timestamp (e.g. 2023-01-31T23:59:59Z)", required=True)
args = parser.parse_args()

start_ts, end_ts = args.start_ts, args.end_ts

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

query = f'from(bucket:"WeatherUnderground")\
    |> range(start: {start_ts}, stop: {end_ts})\
    |> filter(fn: (r) => r["_field"] == "T_db[C]")\
    |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)\
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'

df = query_api.query_data_frame(query)

df['lat'] = df.apply(lambda row: ast.literal_eval(row.coords)[0], axis=1)
df['lon'] = df.apply(lambda row: ast.literal_eval(row.coords)[1], axis=1)
df.index = pd.to_datetime(df['_time'])
df.sort_index(inplace=True)
df.drop(columns=['result', 'table', '_start', '_stop', '_time', 'coords'], inplace=True)


px.set_mapbox_access_token(MAPBOX_TOKEN)

app = Dash(__name__)

app.layout = html.Div(
    [
        dcc.Graph(
            id='graph-with-slider', 
            style=dict(
                height="90vh",
            ),
        ),
        dcc.Slider(
            0,
            len(df.index.unique())-1,
            step=None,
            value=0,
            marks={
                str(i): {
                    "label": (ts - timedelta(hours=24)).strftime("%Y-%m-%d"),
                    "style": {
                        "display": "none",
                        "font-size": "16px",
                        "font-weight": "500",
                        "white-space": "nowrap",
                    },
                } for i, ts in enumerate(df.index.unique())
            },
            id='ts-slider',
        )
    ], 
    style=dict(
        width="90%",
        margin="auto",
    ),
)


@app.callback(
    Output('graph-with-slider', 'figure'),
    Input('ts-slider', 'value')
)
def update_figure(selected_ts):
    filtered_df = df[df.index == df.index.unique()[selected_ts]]
    filtered_df = filtered_df.round({'T_db[C]': 1})
    marker_size = 30

    fig = px.scatter_mapbox(
        filtered_df,
        lat="lat",
        lon="lon",
        size=[marker_size]*len(filtered_df),
        color="T_db[C]",
        color_continuous_scale=px.colors.diverging.RdBu_r,
        range_color=[-10, 40],
        zoom=10,
        size_max=marker_size,
        opacity=0.9,
        mapbox_style="dark",
    )

    fig.update_layout(
        transition_duration=500,
        coloraxis_colorbar_title_text = 'Dry-Bulb Air Temperature [°C]',
        coloraxis_colorbar_orientation = 'h',
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
        )
    )

    fig.update_traces(hovertemplate='%{marker.color} °C')

    return fig


@app.callback(
    Output("ts-slider", "marks"),
    Input("ts-slider", "value"),
    State("ts-slider", "marks"),
)
def update_slider_marks(slider_value, current_marks):
    for k, v in current_marks.items():
        v["style"]["display"] = "block" if slider_value == int(k) else "none"
        current_marks[k] = v

    return current_marks


if __name__ == '__main__':
    app.run_server(debug=True)