import plotly.graph_objects as go
import database as db
from util import labelsTags
import numpy as np
import pandas as pd
import pytz
import geojson as gj
import datetime
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from app import app
from util import geojsons
from util import countryOptions


site = html.Div([
    #html.H1("Aggregated", style={'text-align': 'center'}),
    html.Br(),
    dcc.Tab(
                label="Aggregated",
                value="aggregated",
                children=[
                    html.Div(id="aggregated_options_div",
                             children=[
                                 html.Div("Select a Country:"),
                                 dcc.Dropdown(
                                     id='aggregated_select_country',
                                     options=countryOptions,
                                     value="Portugal",
                                     clearable=False
                                 ),
                                 #html.Div(children=[
                                 html.Div("Select labels:", style={'grid-column': '1', 'grid-row': '2'}),
                                 dcc.Dropdown(id="aggregated_slct_label",
                                              options=labelsTags[["label", "value"]].to_dict('records'),
                                              multi=True,
                                              value="Sea and ocean",
                                              style={'grid-column': '2', 'grid-row': '2'},
                                              optionHeight=55
                                              ),
                                 #html.Br(),
                                 html.Div("Select Month:", style={'grid-column': '3', 'grid-row': '2'}),
                                 dcc.Dropdown(
                                     id='aggregated_select_time',
                                     style = {'grid-column': '4', 'grid-row': '2'}
                                 )],
                             style={'display': 'grid', 'grid-gap': '20px', 'grid-template-columns': '300px 600px 300px 600px ', 'padding':'10px'})
                ]),
    dcc.Graph(id='aggregated_chloropleth_map', config=dict(displayModeBar=True)),
    dcc.Graph(id='aggregated_graph-with-slider'),
], style={'background-color': '#ffffff'}
)

##-------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components
# @app.callback(
#     Output('graph-with-slider', 'figure'),
#     [Input('slct_label', 'value'),
#      Input('select_country', 'value')])
# def update_figure(labels, country_name):
#     figure = go.Figure()
#     if type(labels) is str:
#         labels = [labels]
#     for label in labels:
#         X, Y = db.get_developement_trace(db.geojsons[country_name], label)
#         scatter = go.Scatter(x=list(X), y=list(Y), name=label, mode='lines')
#         figure.add_trace(scatter)
#     return figure

@app.callback(
    Output('aggregated_select_time', 'options'),
    [Input('aggregated_slct_label', 'value'),
     Input('aggregated_select_country', 'value')])
def update_figure(labels, country_name):
    #Generate Months
    return [{"label": "{0:%Y} {0:%B}".format(stamp), "value": stamp} for stamp in db.get_timestamps_in_area(db.geojsons[country_name])]

@app.callback(
    [Output('aggregated_chloropleth_map', 'figure'),
     Output('aggregated_chloropleth_map', 'config')],
    [Input('aggregated_slct_label', 'value'),
     Input('aggregated_select_country', 'value'),
     Input('aggregated_select_time', 'value')])
def update_figure(labels, country_name, time):
    if labels is None or labels == []:
        return go.Figure(), dict(displayModeBar=True)
    if not type(time) is str:
        return go.Figure(), dict(displayModeBar=True)
    if type(labels) is str:
        labels = [labels]
    #Convert Date string into date object
    time = datetime.datetime.strptime(time.split("T")[0], "%Y-%m-%d")
    time = time.replace(tzinfo=pytz.utc)
    outline, center = db.outline_grid(db.geojsons[country_name])

    fig = go.Figure()
    #Setup layout
    fig.update_layout(
        height=700,
        #Background with OSM and the outline of the data available
        mapbox= dict(
            #Use OSM as a background
            style="open-street-map",
            center=dict(
                #Focus on the center of our data
                lon=center.coordinates[0],
                lat=center.coordinates[1]
            ),
            zoom=6,
            #Create a light background for the area that we have data available in general
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
    fulldata = pd.DataFrame()
    framelist = []
    for label in labels:
        #Get the data for each label
        data = db.density_grid(label, db.geojsons[country_name], time)
        fulldata = fulldata.append(data)
        data = data.set_index('geohash').rename(columns={"covered": label})
        framelist.append(data)

    #Create Table with geohash as index and the features and data of the labels in columns
    #This step is necessary since one geohash might have multiple labels, but the information for each label is
    #in a separate dataframe, so we have to join them together and generate e.g. common tooltips
    joined = fulldata[['geohash', 'feature']]\
        .drop_duplicates(subset=['geohash'])\
        .set_index("geohash")\
        .join([frame.iloc[:, 1] for frame in framelist], how='left')
    joined = joined.replace(np.nan, 0)
    texted: pd.DataFrame = pd.DataFrame(["{}: ".format(col) + joined[col].apply(str) + "%" for col in joined.drop(labels='feature', axis=1).columns]).transpose()
    joined["text"] = texted.agg("<br>".join, axis=1)

    #Generates the traces for all labels
    for label in labels:
        otherCoverages = joined.drop(labels=[label, 'feature', 'text'], axis=1)
        otherCoverages['default'] = 0
        data = joined[np.all(joined.loc[:,label].values[:, None] > otherCoverages.values, axis=1)]
        features = gj.FeatureCollection(data['feature'].to_list())
        trace = go.Choroplethmapbox(
            locations=data.index,
            #Sets the Values used for coloring
            z=data[label],
            zmax=100,
            name=label,
            text=data["text"],
            hoverinfo="location+text",
            geojson=features,
            marker=dict(
                line=dict(width=0),
                opacity=0.7
            ),
            #Only the first colorscale is used
            colorscale=labelsTags[labelsTags['value'] == label].iloc[0][2],
            featureidkey="properties.geohash",
            colorbar_title="% Of Tile covered",
            #showscale=label == labels[0]
        )
        fig.add_trace(trace)

    fig.update_traces(showlegend=True, showscale=False)
    fig.update_layout(margin={"r": 100, "t": 0, "l": 0, "b": 0}, legend_title_text='Labels')
    fig.update_geos(fitbounds="geojson", visible=True)
    #fig.show()
    return fig, dict(displayModeBar=True)

@app.callback(
    Output('aggregated_graph-with-slider', 'figure'),
    [Input('aggregated_slct_label', 'value'),
     Input('aggregated_select_country', 'value'),
     Input('aggregated_chloropleth_map', 'selectedData')])
def selectedLineGraph(labels: str, country: str, selectedData):
    if type(labels) is str:
        labels = [labels]

    if selectedData == None or selectedData['points'] == []:
        fetchData = lambda label: db.get_developement_trace(db.geojsons[country], label)
    else:
        #Only retrieve the data for the selected geohashes if there are any selected
        df = pd.DataFrame(selectedData['points'])
        fetchData = lambda label: db.over_time_selected(df['location'].to_list(), label)

    figure = go.Figure()
    for label in labels:
        #Add Traces to graph
        data = fetchData(label)
        scatter = go.Scatter(x=data["attimestamp"], y=data["sum"], name=label, mode='lines')
        figure.add_trace(scatter)
    figure.update_yaxes(
        dict(
            title="Covered in km²",
            #rangemode="tozero"
        )
    )
    return figure

