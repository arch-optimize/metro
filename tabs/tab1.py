from dash import dcc, dash_table, html

from utils.constants import ANALYTICS_GRAPH_OPTIONS, ALL_STATIONS, DAY_OPTIONS, DISC_PROFILES, GRAPH_OPTIONS

MONTH_OPTIONS = [{"label": "All months", "value": -1}] + [
    {"label": str(m), "value": m} for m in range(1, 13)
]

WEEKDAY_OPTIONS = [
    {"label": "Monday", "value": 0},
    {"label": "Tuesday", "value": 1},
    {"label": "Wednesday", "value": 2},
    {"label": "Thursday", "value": 3},
    {"label": "Friday", "value": 4},
    {"label": "Saturday", "value": 5},
    {"label": "Sunday", "value": 6},
]


def render_tab1():
    return html.Div(
        [
            dcc.Store(id="processed-manifest-store"),
            dcc.Store(id="exceptions-store", data=[]),
            dcc.Store(id="tab1-uploaded-npy-data"),
            dcc.Store(id="quality-metrics-store"),

            html.H2("Tab 1 - Processing and Analytics"),

            html.Hr(),

            html.H3("1. Process data"),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Load path (source CSV files)"),
                            dcc.Input(
                                id="load-path-input",
                                type="text",
                                value="",
                                placeholder="/path/to/raw/data",
                                debounce=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "45%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Start date (dd/mm/yyyy)"),
                            dcc.Input(
                                id="process-start-date",
                                type="text",
                                placeholder="01/01/2024",
                                debounce=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "25%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("End date (dd/mm/yyyy)"),
                            dcc.Input(
                                id="process-end-date",
                                type="text",
                                placeholder="31/12/2024",
                                debounce=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "25%", "display": "inline-block", "verticalAlign": "top"},
                    ),
                ],
                style={"marginBottom": "10px"},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Save path (processed output)"),
                            dcc.Input(
                                id="save-path-input",
                                type="text",
                                value="",
                                placeholder="/path/to/processed/output",
                                debounce=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "45%", "display": "inline-block"},
                    ),
                ],
                style={"marginBottom": "12px"},
            ),

            html.Button("Process", id="process-button", n_clicks=0, className="button-primary"),

            dcc.Loading(
                id="process-loading",
                type="circle",
                children=html.Div(id="process-status", style={"marginTop": "10px", "marginBottom": "12px"}),
            ),

            html.Hr(),

            html.H3("2. Analytics — graph parameters"),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Graph type"),
                            dcc.Dropdown(
                                id="graph-dropdown",
                                options=ANALYTICS_GRAPH_OPTIONS,
                                value="all_average",
                                clearable=False,
                            ),
                        ],
                        style={"width": "38%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Date from"),
                            dcc.DatePickerSingle(id="start-date"),
                        ],
                        style={"width": "27%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Date to"),
                            dcc.DatePickerSingle(id="end-date"),
                        ],
                        style={"width": "27%", "display": "inline-block", "verticalAlign": "top"},
                    ),
                ],
                style={"marginBottom": "12px"},
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Day of week"),
                            dcc.Dropdown(
                                id="day-dropdown",
                                options=WEEKDAY_OPTIONS,
                                value=0,
                                clearable=False,
                            ),
                        ],
                        style={"width": "18%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Month"),
                            dcc.Dropdown(
                                id="month-dropdown",
                                options=MONTH_OPTIONS,
                                value=-1,
                                clearable=False,
                            ),
                        ],
                        style={"width": "15%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Year"),
                            dcc.Input(
                                id="year-dropdown",
                                type="number",
                                placeholder="e.g. 2024",
                                min=2000,
                                max=2099,
                                step=1,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "13%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Station (optional)"),
                            dcc.Dropdown(
                                id="stations-dropdown",
                                options=[{"label": s, "value": s} for s in ALL_STATIONS],
                                multi=True,
                                placeholder="All stations",
                            ),
                        ],
                        style={"width": "44%", "display": "inline-block", "verticalAlign": "top"},
                    ),
                ],
                style={"marginBottom": "12px"},
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Analytics data (load) path"),
                            dcc.Input(
                                id="analytics-load-folder",
                                type="text",
                                value="",
                                placeholder="/path/to/processed/npy-npz",
                                debounce=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "48%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Analytics save folder"),
                            dcc.Input(
                                id="analytics-save-folder",
                                type="text",
                                value="",
                                placeholder="/path/to/analytics/output",
                                debounce=True,
                                style={"width": "100%"},
                            ),
                            html.Div(
                                id="analytics-save-warning",
                                style={"fontSize": "11px", "color": "#c0392b", "marginTop": "3px", "minHeight": "14px"},
                            ),
                        ],
                        style={"width": "48%", "display": "inline-block", "verticalAlign": "top"},
                    ),
                ],
                style={"marginBottom": "12px"},
            ),

            html.Div(
                [
                    html.Label("Excluded dates (dd/mm/yyyy, comma-separated)"),
                    dcc.Input(
                        id="excluded-dates-input",
                        type="text",
                        placeholder="20/11/2024, 28/02/2025",
                        debounce=True,
                        style={"width": "100%"},
                    ),
                ],
                style={"marginBottom": "12px"},
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Hour zero"),
                            dcc.Input(
                                id="hour-zero-input",
                                type="number",
                                value=4,
                                min=0,
                                max=23,
                                step=1,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "15%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Illegal boarding rate"),
                            dcc.Input(
                                id="illegal-boarding-rate-input",
                                type="number",
                                value=0.1,
                                min=0.0,
                                max=1.0,
                                step=0.01,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "18%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Special event duration (h)"),
                            dcc.Input(
                                id="special-event-duration-input",
                                type="number",
                                value=5,
                                min=1,
                                max=24,
                                step=1,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "20%", "display": "inline-block", "verticalAlign": "top"},
                    ),
                ],
                style={"marginBottom": "16px"},
            ),

            html.H4("Event dates for deviation calculations", style={"marginTop": "20px"}),
            html.P(
                "Add dates of special events (e.g. strikes, protests). "
                "Each date and its event start hour will be used as non-periodic special dates "
                "in event-deviation analytics. The shared event duration is set above."
            ),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Date"),
                            dcc.DatePickerSingle(id="exception-date"),
                        ],
                        style={"width": "22%", "display": "inline-block", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Event start hour"),
                            dcc.Input(id="exception-start-hour", type="number", min=0, max=23, step=1, style={"width": "100%"}),
                        ],
                        style={"width": "18%", "display": "inline-block", "marginRight": "2%", "verticalAlign": "top"},
                    ),
                    html.Div(
                        [
                            html.Label("\u00a0"),
                            html.Button("Add date", id="add-exception-button", n_clicks=0, className="button-primary"),
                        ],
                        style={"width": "15%", "display": "inline-block", "verticalAlign": "bottom"},
                    ),
                ],
                style={"marginBottom": "10px"},
            ),

            dash_table.DataTable(
                id="exceptions-table",
                columns=[
                    {"name": "Date", "id": "date"},
                    {"name": "Event start hour", "id": "start_hour"},
                ],
                data=[],
                row_deletable=True,
                page_size=5,
                style_table={"overflowX": "auto"},
                style_header={
                    'backgroundColor': '#8a1550',
                    'color': 'white',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
            ),

            html.Div([
                html.Button("Generate graph", id="generate-graph-button", n_clicks=0, className="button-primary", disabled=True),
            ], style={"marginTop": "20px", "marginBottom": "20px"}),

            html.Hr(),

            html.H3("3. Graph"),
            dcc.Loading(
                id="graph-loading",
                type="circle",
                children=dcc.Graph(id="main-graph"),
            ),

            html.Div([
                html.Button("Export Graph (PDF)", id="tab1-export-pdf", className="button-primary"),
                html.Button(
                    "Download analytics files",
                    id="download-analytics-files-btn",
                    n_clicks=0,
                    className="button-primary",
                    style={"marginLeft": "12px"},
                ),
                dcc.Download(id="download-analytics-pdf"),
                dcc.Download(id="download-analytics-files"),
            ], style={"marginTop": "10px", "marginBottom": "10px"}),

            html.Hr(),

            html.H3("4. Processing Quality metrics"),

            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Date from"),
                            dcc.DatePickerSingle(id="quality-date-from"),
                        ],
                        style={"width": "20%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Date to"),
                            dcc.DatePickerSingle(id="quality-date-to"),
                        ],
                        style={"width": "20%", "display": "inline-block", "verticalAlign": "top", "marginRight": "2%"},
                    ),
                    html.Div(
                        [
                            html.Label("Load folder"),
                            dcc.Input(
                                id="quality-load-folder",
                                type="text",
                                value="",
                                placeholder="/path/to/processed/output",
                                debounce=True,
                                style={"width": "100%"},
                            ),
                        ],
                        style={"width": "54%", "display": "inline-block", "verticalAlign": "top"},
                    ),
                ],
                style={"marginBottom": "12px"},
            ),

            html.Button("Load Quality Metrics", id="load-quality-metrics-button", n_clicks=0, className="button-primary"),

            dcc.Loading(
                id="quality-metrics-loading",
                type="circle",
                children=html.Div(id="quality-metrics-status", style={"marginTop": "10px", "color": "green"}),
            ),

            html.Div(id="quality-scalars-display", style={"marginTop": "16px", "marginBottom": "8px"}),

            dcc.Graph(id="quality-unmatched-entries-graph"),
            dcc.Graph(id="quality-unmatched-exits-graph"),
            dcc.Graph(id="quality-same-station-graph"),
            dcc.Graph(id="quality-duplicates-graph"),
            dcc.Graph(id="quality-almost-duplicates-graph"),

            html.H4("Category breakdown by station", style={"marginTop": "20px"}),
            dcc.Dropdown(
                id="quality-station-dropdown",
                options=[{"label": f"{i}: {name}", "value": i} for i, name in enumerate(ALL_STATIONS)],
                placeholder="Select a station…",
                clearable=False,
                style={"marginBottom": "12px"},
            ),
            dcc.Graph(id="quality-category-entries-graph"),
            dcc.Graph(id="quality-category-exits-graph"),

            html.Hr(),

            html.Button("Export metrics (pdf)", id="export-metrics-pdf-button", n_clicks=0, className="button-primary"),
            dcc.Download(id="download-metrics-pdf"),
            html.Br(),
            html.Br(),

            html.Hr(),

            html.H3("5. Process extra data"),

            html.H4("5a. Training data from processed files"),
            html.P(
                "Provide the path to a folder of processed .npy files. "
                "The tool aggregates hourly demand per line and downloads the result as a CSV."
            ),
            html.Div(
                [
                    dcc.Input(
                        id="training-path-input",
                        type="text",
                        placeholder="/path/to/processed/npy/folder",
                        debounce=True,
                        style={"width": "75%", "marginRight": "10px"},
                    ),
                    html.Button("Process", id="training-process-button", n_clicks=0, className="button-primary"),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "8px"},
            ),
            dcc.Loading(
                type="circle",
                children=html.Div(id="training-status", style={"fontSize": "12px", "color": "green", "marginBottom": "10px"}),
            ),
            dcc.Download(id="download-training-csv"),

            html.H4("5b. ATS data processing", style={"marginTop": "20px"}),
            html.P(
                "Provide the path to a folder containing ATS_*.csv files. "
                "The tool computes mean travel times between station pairs and downloads the result as a CSV."
            ),
            html.Div(
                [
                    dcc.Input(
                        id="ats-path-input",
                        type="text",
                        placeholder="/path/to/ats/csv/folder",
                        debounce=True,
                        style={"width": "75%", "marginRight": "10px"},
                    ),
                    html.Button("Process", id="ats-process-button", n_clicks=0, className="button-primary"),
                ],
                style={"display": "flex", "alignItems": "center", "marginBottom": "8px"},
            ),
            dcc.Loading(
                type="circle",
                children=html.Div(id="ats-status", style={"fontSize": "12px", "color": "green", "marginBottom": "10px"}),
            ),
            dcc.Download(id="download-ats-csv"),

            # ── File browser modal ──────────────────────────────────────────────
            html.Div(
                id="file-browser-modal",
                style={"display": "none"},
                children=html.Div(
                    [
                        html.H4(
                            "Select files to download",
                            style={"margin": "0 0 10px 0", "color": "#8a1550"},
                        ),
                        html.Div(id="file-browser-status", style={"fontSize": "12px", "color": "#555", "marginBottom": "10px"}),
                        dcc.Checklist(
                            id="file-browser-checklist",
                            options=[],
                            value=[],
                            labelStyle={"display": "block", "padding": "4px 2px", "fontSize": "13px"},
                            style={
                                "maxHeight": "320px",
                                "overflowY": "auto",
                                "border": "1px solid #eedde5",
                                "borderRadius": "6px",
                                "padding": "8px",
                            },
                        ),
                        html.Div(
                            [
                                html.Button(
                                    "Download selected",
                                    id="file-browser-download-btn",
                                    n_clicks=0,
                                    className="button-primary",
                                ),
                                html.Button(
                                    "Close",
                                    id="file-browser-close-btn",
                                    n_clicks=0,
                                    className="button-primary",
                                    style={"marginLeft": "10px"},
                                ),
                            ],
                            style={"marginTop": "14px"},
                        ),
                    ],
                    style={
                        "background": "white",
                        "borderRadius": "10px",
                        "padding": "28px",
                        "width": "520px",
                        "maxWidth": "90vw",
                        "boxShadow": "0 8px 32px rgba(138,21,80,0.25)",
                    },
                ),
            ),
        ],
        style={"padding": "12px"},
    )
