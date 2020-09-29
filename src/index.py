import dash_core_components as dcc
import dash_html_components as html
from app import app
import aggregatedApp as aggApp
import patchApp as patchApp
from dash.dependencies import Input, Output

app.layout = html.Div(
    children=[dcc.Tabs(
        id="tabs",
        value="aggregated",
        children=[
            dcc.Tab(label="Aggregated Data", value="aggregated", style={'border-left': '0px', 'border-top': '0px', 'border-bottom': '0px'}),
            dcc.Tab(label="Raw Data", value="patches", style={'border-right': '0px', 'border-top': '0px', 'border-bottom': '0px'})
        ],
        style={'padding': '0px 10%', 'background-color': '#f9f9f9'}
    ),
        html.Div(id="page_content")
    ]
)


@app.callback(
    Output('page_content', 'children'),
    [Input('tabs', 'value')])
def update_window(tab: str):
    if tab == "aggregated":
        return aggApp.site
    elif tab == "patches":
        return patchApp.site


if __name__ == '__main__':
    app.run_server(debug=True)
