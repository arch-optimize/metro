from dash import dcc, html, dash_table


_UPLOAD_STYLE = {
    "width": "100%",
    "height": "80px",
    "lineHeight": "80px",
    "borderWidth": "2px",
    "borderStyle": "dashed",
    "borderRadius": "8px",
    "borderColor": "#8a1550",
    "textAlign": "center",
    "color": "#8a1550",
    "cursor": "pointer",
    "backgroundColor": "#fdf8fb",
    "fontSize": "13px",
}


def _upload_box(component_id, label):
    return html.Div(
        [
            html.Label(label, style={"fontWeight": "bold", "fontSize": "12px", "marginBottom": "4px", "display": "block"}),
            dcc.Upload(
                id=component_id,
                children=html.Div(["Drag & drop or ", html.A("select CSV")]),
                style=_UPLOAD_STYLE,
                multiple=False,
            ),
            html.Div(id=f"{component_id}-name", style={"fontSize": "11px", "color": "#555", "marginTop": "3px"}),
        ]
    )


def render_tab2():
    return html.Div(
        [
            dcc.Store(id="tab2-demand-store"),
            dcc.Store(id="tab2-schedule-store"),
            html.H2("Tab 2 - Scheduling & Optimization"),
            html.Hr(),

            html.H3("1. Input Processed Demand"),
            html.Div(
                [
                    html.Label("Path to processed .npy file"),
                    html.Div(
                        [
                            dcc.Input(
                                id="tab2-npy-path",
                                type="text",
                                placeholder="/path/to/demand_matrix.npy",
                                style={"width": "80%", "marginRight": "10px"},
                            ),
                            html.Button("Load", id="tab2-load-npy-button", n_clicks=0, className="button-primary"),
                        ],
                        style={"display": "flex", "alignItems": "center", "margin": "10px 0"},
                    ),
                ],
            ),
            html.Div(id="tab2-upload-status", style={"fontSize": "12px", "color": "blue", "marginBottom": "10px"}),

            html.Hr(),

            html.H3("2. Global Parameters"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Line selection"),
                            dcc.Dropdown(
                                id="tab2-line-dropdown",
                                options=[
                                    {"label": "Line 1", "value": 1},
                                    {"label": "Line 2", "value": 2},
                                    {"label": "Line 3", "value": 3},
                                ],
                                value=1,
                                clearable=False,
                            ),
                        ],
                        style={"width": "30%", "display": "inline-block"},
                    ),
                    html.Div(
                        [
                            html.Label("Minimum Time Between Trains (sec)"),
                            dcc.Input(
                                id="tab2-min-headway",
                                type="number",
                                value=60,
                                style={"width": "100%"},
                            ),
                        ],
                        style={
                            "width": "30%",
                            "display": "inline-block",
                            "marginLeft": "3%",
                        },
                    ),
                    html.Div(
                        [
                            html.Label("Maximum Capacity"),
                            dcc.Input(
                                id="tab2-max-capacity",
                                type="number",
                                value=800,
                                style={"width": "100%"},
                            ),
                        ],
                        style={
                            "width": "30%",
                            "display": "inline-block",
                            "marginLeft": "3%",
                        },
                    ),
                ],
                style={"marginBottom": "12px"},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Solver time limit (sec)"),
                            dcc.Input(
                                id="tab2-time-limit",
                                type="number",
                                value=300,
                                min=10,
                                step=10,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "30%", "display": "inline-block"},
                    ),
                ],
                style={"marginBottom": "20px"},
            ),

            html.H3("3. Loops Configuration"),
            html.P("Click the button below to add parameters for each specific train loop."),
            html.Button(
                "ADD LOOP",
                id="add-loop-button",
                n_clicks=0,
                className="button-primary",
                style={"marginBottom": "15px"},
            ),
            html.Div(id="loops-container", children=[]),

            html.Hr(),

            html.H3("4. Objective Weights"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Importance of minimizing waiting time"),
                            html.Div(
                                [
                                    dcc.Slider(
                                        id="tab2-waiting-weight",
                                        min=0,
                                        max=100,
                                        value=62,
                                        step=1,
                                        marks={0: "0", 100: "100"},
                                    ),
                                    dcc.Input(
                                        id="tab2-waiting-input",
                                        type="number",
                                        value=62,
                                        style={"width": "65px", "marginLeft": "15px"},
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                    html.Div(
                        [
                            html.Label("Importance of minimizing number of scheduled trains"),
                            html.Div(
                                [
                                    dcc.Slider(
                                        id="tab2-trains-weight",
                                        min=0,
                                        max=100,
                                        value=35,
                                        step=1,
                                        marks={0: "0", 100: "100"},
                                    ),
                                    dcc.Input(
                                        id="tab2-trains-input",
                                        type="number",
                                        value=35,
                                        style={"width": "65px", "marginLeft": "15px"},
                                    ),
                                ],
                                style={"display": "flex", "alignItems": "center"},
                            ),
                        ],
                    ),
                ],
                style={"marginBottom": "30px"},
            ),

            html.H3("5. Phase-Out"),
            html.Div([
                html.Label("phase out duration(seconds)"),
                html.Br(),
                dcc.Input(id="tab2-phase-out", type="number", value=3600, style={"width": "200px"}),
            ], style={"marginBottom": "20px"}),

            html.Hr(),

            html.Div(
                [
                    html.Button(
                        "Generate Schedule",
                        id="tab2-preview-button",
                        className="button-primary"
                    ),
                    html.Button(
                        "Export PDF Report",
                        id="tab2-export-pdf",
                        className="button-primary",
                        style={"marginLeft": "15px"},
                    ),
                    html.Button(
                        "Export Schedule CSV",
                        id="tab2-export-csv",
                        className="button-primary",
                        style={"marginLeft": "15px"},
                    ),
                    dcc.Download(id="download-schedule-pdf"),
                    dcc.Download(id="download-schedule-csv"),
                ],
                style={"margin": "20px 0"},
            ),

            dcc.Loading(
                id="scheduling-loading",
                type="circle",
                children=[
                    dcc.Graph(id="tab2-supply-demand-graph"),
                    dcc.Graph(id="tab2-trains-graph"),
                    html.H3("6. Generated Timetable"),
                    dash_table.DataTable(
                        id="tab2-schedule-table",
                        columns=[
                            {"name": "Direction", "id": "direction"},
                            {"name": "Departure (sec)", "id": "departure"},
                        ],
                        page_size=15,
                        style_table={"overflowX": "auto"},
                        style_header={
                            'backgroundColor': '#8a1550',
                            'color': 'white',
                            'fontWeight': 'bold',
                            'textAlign': 'center'
                        },
                        style_cell={'textAlign': 'center'},
                    ),
                ]
            ),
            html.Hr(),

            html.H3("7. Syntagma Arrivals"),
            html.P(
                "Upload one departure-times CSV per loop direction "
                "(the files exported by this tool work directly). "
            ),

            html.Div(
                [
                    _upload_box("synt-upload-red-anthoupoli",   "anthoupoli->elliniko"),
                    _upload_box("synt-upload-red-elliniko",     "elliniko->Anthoupoli"),
                    _upload_box("synt-upload-blue-dt1",         "dimotiko theatro->plakentias"),
                    _upload_box("synt-upload-blue-doukissis",   "plakentias->dimotiko theatro"),
                    _upload_box("synt-upload-blue-dt2",         "dimotiko theatro->airport"),
                    _upload_box("synt-upload-blue-aerodromio",  "airport->dimotiko theatro"),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr 1fr",
                    "gap": "16px",
                    "marginBottom": "20px",
                },
            ),

            html.Div([
                html.Label("Grouping time interval size (seconds)"),
                html.Br(),
                dcc.Input(
                    id="synt-bin-size",
                    type="number",
                    value=300,
                    min=60,
                    step=60,
                    style={"width": "150px"},
                ),
            ], style={"marginBottom": "16px"}),

            html.Button(
                "Examine Syntagma arrivals",
                id="run-syntagma-button",
                n_clicks=0,
                className="button-primary",
                style={"marginBottom": "20px"},
            ),

            dcc.Loading(
                type="circle",
                children=dcc.Graph(id="syntagma-arrivals-graph"),
            ),
        ],
        style={"padding": "20px"},
    )