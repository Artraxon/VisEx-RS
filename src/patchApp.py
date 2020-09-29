import dash  # (version 1.12.0) pip install dash
import plotly.graph_objects as go
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import geojson as gj
from util import labelsTags
from app import app
import datetime as dt
import database as db
from util import geojsons
from util import countryOptions
import re

site = html.Div([
    #html.H1("Raw Data", style={'text-align': 'center'}),
    html.Br(),
    dcc.Tab(
        label="Raw data",
        value="patches",
        children=[
            html.Div(id="patch_options_div",
                     children=[
                         html.Div("Narrow Down by country:",
                                  style = {'grid-column': '1', 'grid-row': '1'}
                                  ),
                         dcc.Dropdown(
                             id='patch_select_country',
                             options=countryOptions,
                             value="Portugal",
                             style={'grid-column': '2', 'grid-row': '1'},
                             clearable=False
                         ),
                         #Setup DateRange Selection
                         html.Div("Narrow Down by Dates:",
                                  style = {'grid-column': '3', 'grid-row': '1'}
                                  ),
                         dcc.DatePickerRange(
                             id='patch_select_time',
                             min_date_allowed=dt.datetime(2017, 6, 13),
                             max_date_allowed=dt.datetime(2018, 5, 29),
                             initial_visible_month=dt.datetime(2017, 6, 13),
                             start_date=dt.datetime(2017, 6, 13),
                             end_date=dt.datetime(2018, 5, 29),
                             style={'grid-column': '4', 'grid-row': '1'}
                         ),
                         html.Div("Select tile sources",
                                  style={'grid-column': '1', 'grid-row': '2'}
                                  ),
                         dcc.Dropdown(
                             id='patch_select_patch',
                             multi=True,
                             style={'grid-column-start': '2', 'grid-column-end': '4', 'grid-row': '2'}

                         ),
                         html.Div("Narrow Down patches by label:",
                                  style = {'grid-column': '1', 'grid-row': '4'}
                                  ),
                         dcc.Dropdown(id="patch_select_label",
                                      options=labelsTags[["label", "value"]].to_dict('records'),
                                      # able to select multiple stocks at the same time 
                                      multi=True,
                                      #a selected default value
                                      value="Sea and ocean",
                                      style={'grid-column': '2', 'grid-row': '3'},
                                      optionHeight=55
                                      ),
                         dcc.RadioItems(id="patch_select_mode",
                                        options=[
                                            {'label': "Match All", 'value': 'nil'},
                                            {'label': "Match Any", 'value': 't'}],
                                        value='t',
                                        style={'grid-column': '3', 'grid-row': '3'},
                         labelStyle={'display': 'inline-block', 'grid-column-start': '3', 'grid-column-end': '4'})
                     ]
                     , style = {'display': 'grid', 'grid-gap': '20px', 'grid-template-columns': '15% 35% 15% 35%', 'padding':'10px'}
                     )
            ,
#dcc.Graph(id='patch_graph-with-slider'),
            html.Br(),
            dcc.Graph(id='patch_chloropleth_map')
        ]
    )
], style={'background-color': '#ffffff', }
)
#callback will handle the communication between our dropdown menu and our graph
@app.callback(
    Output('patch_select_patch', 'options'),
    [Input('patch_select_time', 'start_date'),
     Input('patch_select_time', 'end_date'),
     Input('patch_select_country', 'value')])
     
     
def update_patches(dateStart, dateEnd, country_name):
    #Narrows down tile source options based on date range and country
    dateStart = dt.datetime.strptime(re.split('T| ', dateStart)[0], '%Y-%m-%d')
    dateEnd = dt.datetime.strptime(re.split('T| ', dateEnd)[0], '%Y-%m-%d')
    options = [{"label": sourceName[0], "value": sourceName[0]} for sourceName in db.findTileSources(dateStart, dateEnd, country_name).itertuples(index=False)]
    return options

@app.callback(
    Output('patch_chloropleth_map', 'figure'),
    [Input('patch_select_label', 'value'),
     Input('patch_select_patch', 'value'),
     Input('patch_select_mode', 'value')])
def update_path_figure(labels, tileSources, mode: str):
    mode = mode == 't'
    if type(labels) is str:
        labels = [labels]
    if type(tileSources) is str:
        tileSources = [tileSources]

    fig = go.Figure()
    if tileSources == [] or tileSources is None:
        return fig

    outline, center = db.outlinePatches(tileSources)
    fig.update_layout(
        height=700,
        #Background with OSM and the outline of the data available
        mapbox= dict(
            style="open-street-map",
            center=dict(
                lon=center.coordinates[0],
                lat=center.coordinates[1]
            ),
            zoom=6,
            layers=[
                dict(
                    source=outline,
                    type="fill",
                    opacity=0.2,
                    color="#FAFAFA"
                )
            ]
        ),
    )

    for source in tileSources:
        data = db.findPatches(source, labels, matchAny=mode)
        if data.size == 0:
            continue
        #Set the text of each path to all the labels, each on one line
        data['text'] = data['labels'].apply("<br>".join)
        features = gj.FeatureCollection(data['feature'].to_list())
        trace = go.Choroplethmapbox(
            locations=data['patch_name'],
            name=source,
            z=data['val'],
            zmin=0,
            zmax=1,
            text=data["text"],
            hoverinfo="location+text",
            geojson=features,
            marker=dict(
                line=dict(width=0),
                opacity=0.7
            ),
            #color every patch black
            colorscale=[[0, 'rgb(255, 255, 255)'], [1, 'rgb(0, 0, 0)']],
            featureidkey="properties.patch_name",
            showscale=False
        )
        fig.add_trace(trace)

    fig.update_layout(margin={"r": 100, "t": 0, "l": 0, "b": 0})
    fig.update_geos(fitbounds="geojson", visible=True)
    return fig







