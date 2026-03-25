from datetime import datetime
from pathlib import Path
import params
import numpy as np
import dash
from dash import Dash, Input, Output, State, callback_context, dcc, html, no_update, ALL
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from services.processing import process_uploaded_dataframe, processed_to_training, process_ats
from services.analytics import display_extra_info, select_graph_to_display
from services.processing import process_uploaded_dataframe
from services.scheduling import find_syntagma_arrivals, run_optimization_pipeline, schedule_to_departures
from utils.reports import generate_pdf_report, generate_metrics_pdf_report
from tabs.tab1 import render_tab1
from tabs.tab2 import render_tab2
from tabs.tab3 import render_tab3, register_tab3_callbacks
from utils.constants import ALL_STATIONS, ANALYTICS_GRAPH_OPTIONS, ANALYTICS_SPECIAL_GRAPH_TYPES, DISC_PROFILES

_GRAPH_LABEL = {opt["value"]: opt["label"] for opt in ANALYTICS_GRAPH_OPTIONS}

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
register_tab3_callbacks(app)
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Metro Analytics</title>
        {%favicon%}
        {%css%}
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #fdfafb; }
            
            h1, h2, h3 { color: #8a1550; }
            
            .section-card { 
                background-color: white; 
                padding: 20px; 
                border-radius: 10px; 
                box-shadow: 0 4px 6px rgba(138, 21, 80, 0.1); /* Subtle purple shadow */
                margin-bottom: 25px; 
                border-left: 5px solid #8a1550; /* Left accent border */
            }
            
            /* Tabs Styling */
            .tab-container { background-color: #fdfafb; }
            .nav-tabs .nav-link.active {
                color: #8a1550 !important;
                border-bottom: 3px solid #8a1550 !important;
            }

            /* Global Buttons */
            .button-primary { 
                background-color: #8a1550 !important; 
                color: white !important; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 5px; 
                cursor: pointer; 
                transition: background-color 0.3s;
            }
            .button-primary:hover { background-color: #6d1140 !important; }
            .button-primary:disabled { background-color: #c4a0b4 !important; cursor: not-allowed; }
            
            hr { border: 0; height: 1px; background: #eedde5; margin: 20px 0; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div(
    [
        html.H1("Metro Analytics Dashboard"),
        dcc.Tabs(
            id="main-tabs",
            value="tab1",
            children=[
                dcc.Tab(label="Analytics", value="tab1"),
                dcc.Tab(label="Scheduling", value="tab2"),
                dcc.Tab(label="Model", value="tab3"),
            ],
            style={'height': '50px'},
            colors={
                "border": "#eedde5",
                "primary": "#8a1550",
                "background": "#fdfafb",
            }
        ),
        # All tabs rendered at startup so their state is preserved on tab switch
        html.Div(render_tab1(), id="tab1-content", style={"display": "block"}),
        html.Div(render_tab2(), id="tab2-content", style={"display": "none"}),
        html.Div(render_tab3(), id="tab3-content", style={"display": "none"}),
    ]
)


@app.callback(
    Output("tab1-content", "style"),
    Output("tab2-content", "style"),
    Output("tab3-content", "style"),
    Input("main-tabs", "value"),
)
def switch_tab(tab):
    show = {"display": "block"}
    hide = {"display": "none"}
    return (
        show if tab == "tab1" else hide,
        show if tab == "tab2" else hide,
        show if tab == "tab3" else hide,
    )


@app.callback(
    Output("processed-manifest-store", "data"),
    Output("stations-dropdown", "options"),
    Output("process-status", "children"),
    Input("process-button", "n_clicks"),
    Input("load-path-input", "value"),
    Input("save-path-input", "value"),
    Input("process-start-date", "value"),
    Input("process-end-date", "value"),
)
def process_uploaded_file(n_clicks, l_path, s_path, s_date, f_date):
    trigger = callback_context.triggered_id if callback_context.triggered else None
    if trigger != "process-button":
        return no_update, no_update, ""

    if not l_path or not s_path or not s_date or not f_date:
        return no_update, [], "Please fill in all four fields (load path, save path, start date, end date)."

    try:
        process_uploaded_dataframe(s_date, f_date, l_path, s_path)
        station_options = [{"label": s, "value": s} for s in ALL_STATIONS]
        status = f"Processing complete for {s_date} → {f_date}. Output written to: {s_path}"
        return no_update, station_options, status

    except Exception as e:
        return no_update, [], f"Processing failed: {e}"

@app.callback(
    Output("tab1-upload-status", "children"),
    Output("tab1-uploaded-npy-data", "data"),
    Input("npy-analytics-path", "value"),
    prevent_initial_call=True
)
def handle_tab1_direct_npy_path(npy_path):
    if not npy_path:
        return no_update, no_update
    try:
        data = np.load(npy_path)
        return f"Loaded: {npy_path} — shape: {data.shape}", data.tolist()
    except Exception as e:
        return f"Load failed: {e}", no_update


def _time_labels(n_slices, hour_zero, start_minute=None):
    """Return HH:MM strings for each 2-minute slice.

    start_minute overrides the default hour_zero-based start when provided
    (used e.g. for event_deviation whose window doesn't start at hour_zero).
    """
    if start_minute is None:
        start_minute = int(hour_zero if hour_zero is not None else 4) * 60
    return [
        f"{((start_minute + i * 2) // 60) % 24:02d}:{(start_minute + i * 2) % 60:02d}"
        for i in range(n_slices)
    ]


@app.callback(
    Output("main-graph", "figure"),
    Input("generate-graph-button", "n_clicks"),
    State("graph-dropdown", "value"),
    State("analytics-load-folder", "value"),
    State("analytics-save-folder", "value"),
    State("start-date", "date"),
    State("end-date", "date"),
    State("day-dropdown", "value"),
    State("month-dropdown", "value"),
    State("year-dropdown", "value"),
    State("stations-dropdown", "value"),
    State("exceptions-store", "data"),
    State("excluded-dates-input", "value"),
    State("hour-zero-input", "value"),
    State("illegal-boarding-rate-input", "value"),
    State("special-event-duration-input", "value"),
    State("tab1-uploaded-npy-data", "data"),
    prevent_initial_call=True,
)
def update_graph(
    n_clicks,
    graph_type,
    load_folder,
    save_folder,
    start_date,
    end_date,
    day,
    month,
    year,
    selected_stations,
    exceptions,
    excluded_dates_str,
    hour_zero,
    illegal_boarding_rate,
    special_event_duration,
    uploaded_npy,
):
    if uploaded_npy:
        try:
            arr = np.array(uploaded_npy).reshape((24 * 30, 70, 70))
            station_idx = -1
            if selected_stations:
                try:
                    station_idx = ALL_STATIONS.index(selected_stations[0])
                except ValueError:
                    station_idx = -1
            
            if station_idx == -1:
                y_vals = np.sum(arr, axis=(1, 2))
            else:
                y_vals = np.sum(arr, axis=1)[:, station_idx].flatten()

            return {
                "data": [{"x": _time_labels(len(y_vals), hour_zero), "y": [float(x) for x in y_vals], "type": "scatter", "mode": "lines", "name": "Uploaded Data"}],
                "layout": {"title": "Uploaded Data Analytics", "xaxis": {"title": "Time of day"}},
            }
        except Exception as e:
            return {"data": [], "layout": {"title": f"Error processing uploaded NPY: {e}"}}

    if not graph_type:
        return {"data": [], "layout": {"title": "Select a graph type"}}
    if not load_folder:
        return {"data": [], "layout": {"title": "Enter Analytics data (load) path"}}
    if not save_folder:
        return {"data": [], "layout": {"title": "Please enter an Analytics save folder path"}}
    if not start_date or not end_date:
        return {"data": [], "layout": {"title": "Select date range"}}

    exceptions = exceptions or []
    non_periodic_special_dates = []
    special_hours = []
    for row in exceptions:
        if row.get("date"):
            try:
                non_periodic_special_dates.append(
                    datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
                )
                h = row.get("start_hour")
                special_hours.append(int(h) if h is not None else 0)
            except (ValueError, TypeError):
                pass
    if non_periodic_special_dates and len(special_hours) != len(non_periodic_special_dates):
        special_hours = [0] * len(non_periodic_special_dates)

    excluded_dates = []
    if excluded_dates_str:
        excluded_dates = [d.strip() for d in excluded_dates_str.split(",") if d.strip()]

    date_from = datetime.strptime(start_date, "%Y-%m-%d")
    date_to = datetime.strptime(end_date, "%Y-%m-%d")

    station_idx = -1
    if selected_stations:
        try:
            station_idx = ALL_STATIONS.index(selected_stations[0])
        except ValueError:
            station_idx = -1

    month_val = month if month is not None else -1
    year_val = str(year) if year is not None else "-1"
    if month_val not in (-1, None) and 1 <= month_val <= 12:
        month_str = str(month_val).zfill(2)
    else:
        month_str = str(month_val)

    try:
        result = select_graph_to_display(
            date_from=date_from,
            date_to=date_to,
            non_periodic_special_dates=non_periodic_special_dates,
            special_hours=special_hours,
            excluded_dates=excluded_dates,
            load_folder=load_folder,
            save_folder=save_folder or "",
            graph_type=graph_type,
            day=day if day is not None else 0,
            month=month_str,
            year=year_val,
            station=station_idx,
            hour_zero=hour_zero if hour_zero is not None else 4,
            special_event_duration=special_event_duration if special_event_duration is not None else 5,
            illegal_boarding_rate=illegal_boarding_rate if illegal_boarding_rate is not None else 0.1,
        )
        if result is None:
            return {"data": [], "layout": {"title": "No data returned — check parameters and paths"}}

        graph_label = _GRAPH_LABEL.get(graph_type, graph_type)
        graph_title = f"{graph_label} — 2-minute demand"

        if isinstance(result, list):
            n = len(result)
            if n == 0:
                return {"data": [], "layout": {"title": "No series to plot"}}
            fig = make_subplots(rows=n, cols=1, subplot_titles=[f"{graph_title} — series {i+1}" for i in range(n)])
            hz = hour_zero if hour_zero is not None else 4
            for i, arr in enumerate(result):
                a = np.asarray(arr)
                x_vals = _time_labels(len(a.flatten()), hz)
                fig.add_trace(
                    {"x": x_vals, "y": a.flatten().tolist(), "type": "scatter", "mode": "lines"},
                    row=i + 1,
                    col=1,
                )
            fig.update_xaxes(title_text="Time of day")
            fig.update_layout(height=350 * n, title_text=graph_title)
            return fig
        else:
            arr = np.asarray(result)
            hz = hour_zero if hour_zero is not None else 4
            # For event_deviation the window starts at spec_time-1, not hour_zero
            if graph_type == "event_deviation" and special_hours:
                start_min = (special_hours[0] - 1) * 60
            else:
                start_min = None
            x_vals = _time_labels(len(arr.flatten()), hz, start_minute=start_min)
            return {
                "data": [{"x": x_vals, "y": arr.flatten().tolist(), "type": "scatter", "mode": "lines"}],
                "layout": {"title": graph_title, "xaxis": {"title": "Time of day"}},
            }
    except Exception as e:
        return {"data": [], "layout": {"title": f"Error: {e}"}}


@app.callback(
    Output("start-date", "disabled"),
    Output("end-date", "disabled"),
    Output("year-dropdown", "disabled"),
    Output("day-dropdown", "disabled"),
    Output("month-dropdown", "disabled"),
    Input("graph-dropdown", "value"),
)
def toggle_controls_for_graph(graph_type):
    return False, False, False, False, False


@app.callback(
    Output("analytics-save-warning", "children"),
    Output("generate-graph-button", "disabled"),
    Input("analytics-save-folder", "value"),
)
def validate_save_folder(save_folder):
    if not save_folder or not save_folder.strip():
        return "Analytics save folder is required.", True
    return "", False


@app.callback(
    Output("exceptions-store", "data"),
    Output("exceptions-table", "data"),
    Input("add-exception-button", "n_clicks"),
    Input("exceptions-table", "data"),
    State("exceptions-store", "data"),
    State("exception-date", "date"),
    State("exception-start-hour", "value"),
    prevent_initial_call=True,
)
def manage_exceptions(n_clicks, table_data, existing, ex_date, start_hour):
    trigger = callback_context.triggered_id if callback_context.triggered else None

    if trigger == "add-exception-button":
        existing = existing or []
        if not ex_date:
            return existing, existing
        new_row = {"date": ex_date, "start_hour": start_hour if start_hour is not None else 0}
        updated = existing + [new_row]
        return updated, updated
    else:
        # A row was deleted from the table — sync store; no_update avoids circular trigger
        synced = table_data or []
        return synced, no_update


@app.callback(
    Output("tab2-demand-store", "data"),
    Output("tab2-upload-status", "children"),
    Input("tab2-load-npy-button", "n_clicks"),
    State("tab2-npy-path", "value"),
    prevent_initial_call=True
)
def load_tab2_npy(n_clicks, npy_path):
    if not npy_path:
        return no_update, "Please enter a path to a .npy file."
    try:
        data = np.load(npy_path)
        return data.tolist(), f"Loaded: {npy_path} — shape: {data.shape}"
    except Exception as e:
        return no_update, f"Load failed: {e}"


@app.callback(
    Output("loops-container", "children"),
    Input("add-loop-button", "n_clicks"),
    Input({'type': 'loop-delete-btn', 'index': ALL}, 'n_clicks'),
    State("loops-container", "children"),
    prevent_initial_call=True
)
def manage_loops(add_clicks, delete_clicks, children):
    triggered_id = callback_context.triggered_id

    # ── Delete a loop ──────────────────────────────────────────────────────────
    if isinstance(triggered_id, dict) and triggered_id.get("type") == "loop-delete-btn":
        idx = triggered_id["index"]
        children = [
            c for c in children
            if not (
                isinstance(c, dict)
                and c.get("props", {}).get("id", {}).get("type") == "loop-wrapper"
                and c.get("props", {}).get("id", {}).get("index") == idx
            )
        ]
        return children

    # ── Add a loop ─────────────────────────────────────────────────────────────
    n = add_clicks
    new_loop = html.Div(
        id={"type": "loop-wrapper", "index": n},
        children=[
            html.Div([
                html.B(f"Loop {n}", style={"fontSize": "15px"}),
                html.Button(
                    "✕",
                    id={"type": "loop-delete-btn", "index": n},
                    n_clicks=0,
                    style={
                        "marginLeft": "auto",
                        "background": "none",
                        "border": "none",
                        "fontSize": "16px",
                        "cursor": "pointer",
                        "color": "#8a1550",
                        "lineHeight": "1",
                        "padding": "0 4px",
                    },
                ),
            ], style={"display": "flex", "alignItems": "center"}),
            # Row 1: station range + max wait time
            html.Div([
                html.Div([
                    html.Label("Start station index", style={"fontSize": "12px"}),
                    dcc.Input(id={'type': 'loop-start-idx', 'index': n}, type="number", value=0, min=0, step=1, style={"width": "100%"}),
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("End station index", style={"fontSize": "12px"}),
                    dcc.Input(id={'type': 'loop-end-idx', 'index': n}, type="number", value=19, min=0, step=1, style={"width": "100%"}),
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("Max time between trains (min)", style={"fontSize": "12px"}),
                    dcc.Input(id={'type': 'loop-max-time', 'index': n}, type="number", value=10, min=1, step=1, style={"width": "100%"}),
                ], style={"width": "28%"}),
            ], style={"display": "flex", "gap": "3%", "marginTop": "8px", "marginBottom": "8px"}),
            # Row 2: train counts at each end
            html.Div([
                html.Div([
                    html.Label("Initial trains at Origin", style={"fontSize": "12px"}),
                    dcc.Input(id={'type': 'loop-avail-orig', 'index': n}, type="number", value=8, min=0, step=1, style={"width": "100%"}),
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("Initial trains at Destination", style={"fontSize": "12px"}),
                    dcc.Input(id={'type': 'loop-avail-dest', 'index': n}, type="number", value=6, min=0, step=1, style={"width": "100%"}),
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("Max trains at Origin", style={"fontSize": "12px"}),
                    dcc.Input(id={'type': 'loop-max-orig', 'index': n}, type="number", value=10, min=1, step=1, style={"width": "100%"}),
                ], style={"width": "22%"}),
                html.Div([
                    html.Label("Max trains at Destination", style={"fontSize": "12px"}),
                    dcc.Input(id={'type': 'loop-max-dest', 'index': n}, type="number", value=10, min=1, step=1, style={"width": "100%"}),
                ], style={"width": "22%"}),
            ], style={"display": "flex", "gap": "3%"}),
        ],
        style={"border": "1px solid #ddd", "borderRadius": "6px", "padding": "12px", "margin": "8px 0", "backgroundColor": "#fdf8fb"},
    )
    children.append(new_loop)
    return children

# Weight Sync Callbacks (to link Sliders and Inputs)
@app.callback(Output("tab2-waiting-input", "value"), Output("tab2-waiting-weight", "value"), Input("tab2-waiting-weight", "value"), Input("tab2-waiting-input", "value"))
def sync_w1(s, i):
    ctx = dash.callback_context
    return (s, s) if ctx.triggered_id == "tab2-waiting-weight" else (i, i)

@app.callback(Output("tab2-trains-input", "value"), Output("tab2-trains-weight", "value"), Input("tab2-trains-weight", "value"), Input("tab2-trains-input", "value"))
def sync_w2(s, i):
    ctx = dash.callback_context
    return (s, s) if ctx.triggered_id == "tab2-trains-weight" else (i, i)

@app.callback(
    Output("tab2-schedule-table", "data"),
    Output("tab2-supply-demand-graph", "figure"),
    Output("tab2-trains-graph", "figure"),
    Output("tab2-schedule-store", "data"),
    Input("tab2-preview-button", "n_clicks"),
    State("tab2-demand-store", "data"),
    State("tab2-line-dropdown", "value"),
    State("tab2-min-headway", "value"),
    State("tab2-max-capacity", "value"),
    State("tab2-phase-out", "value"),
    State("tab2-time-limit", "value"),
    State("tab2-waiting-input", "value"),
    State("tab2-trains-input", "value"),
    State({'type': 'loop-start-idx', 'index': ALL}, 'value'),
    State({'type': 'loop-end-idx',   'index': ALL}, 'value'),
    State({'type': 'loop-max-time',  'index': ALL}, 'value'),
    State({'type': 'loop-avail-orig','index': ALL}, 'value'),
    State({'type': 'loop-avail-dest','index': ALL}, 'value'),
    State({'type': 'loop-max-orig',  'index': ALL}, 'value'),
    State({'type': 'loop-max-dest',  'index': ALL}, 'value'),
    prevent_initial_call=True
)
def run_scheduling_pipeline(n, demand, line, min_h, max_cap, po, time_limit, w_wait, w_train,
                            l_starts, l_ends, l_max_wait, av_o, av_d, mx_o, mx_d):
    if not demand:
        return [], {}, {}, no_update
    if not l_starts:
        return [], {}, {}, no_update

    # Build structured parameters — one entry per loop
    loops         = [[int(l_starts[i]), int(l_ends[i])] for i in range(len(l_starts))]
    initial_state = [(int(av_o[i]), int(av_d[i])) for i in range(len(av_o))]
    max_at_ends   = [(int(mx_o[i]), int(mx_d[i])) for i in range(len(mx_o))]
    max_wait_min  = [int(v) for v in l_max_wait]

    x_scheduled, x1_scheduled, tot_new, tot_boarded, tot_trains, tot_trains_opposite, overhead, _ = run_optimization_pipeline(
        demand, line, min_h, max_wait_min, initial_state, max_at_ends, w_wait, w_train, max_cap,
        phase_out_val=10_000,
        loops=loops,
        time_limit=int(time_limit) if time_limit else 300,
        phase_out_seconds=int(po) if po else 3600,
    )

    # Build time-of-day x-axis labels for simulation output.
    # simulate_loops uses group_results_n_slices=5 (default), so each output
    # point spans 5 * t_unit seconds.  Service starts at 04:00 (4 * 3600 s).
    _GROUP = 5
    _START = 4 * 3600  # 04:00 in seconds from midnight
    _step  = _GROUP * (int(min_h) // 2 if min_h else 30)
    sim_x = [
        f"{((_START + i * _step) // 3600)%24:02d}:{((_START + i * _step) % 3600) // 60:02d}"
        for i in range(len(tot_new))
    ]

    # Passenger flow graph (mirrors ax1 in local code)
    fig_passengers = go.Figure()
    fig_passengers.add_trace(go.Scatter(x=sim_x, y=[float(x) for x in tot_new],    name="New passengers",         mode='lines', line=dict(width=3)))
    fig_passengers.add_trace(go.Scatter(x=sim_x, y=[float(x) for x in tot_boarded],name="Boarded",                mode='lines', line=dict(width=3)))
    fig_passengers.add_trace(go.Scatter(x=sim_x, y=[float(x) for x in overhead],   name="New waiting passengers", mode='lines', line=dict(width=3)))
    fig_passengers.update_layout(title="Passenger Flow", xaxis_title="Time of day", yaxis_title="Passengers", legend=dict(orientation="h"))

    # Active trains per loop graph (mirrors ax2 in local code)
    fig_trains = go.Figure()
    for i in range(len(tot_trains)):
        fig_trains.add_trace(go.Scatter(x=sim_x, y=[float(x) for x in tot_trains[i]],          name=f"total_trains_loop_{i}",          mode='lines', line=dict(width=3)))
        fig_trains.add_trace(go.Scatter(x=sim_x, y=[float(x) for x in tot_trains_opposite[i]], name=f"total_trains_opposite_loop_{i}", mode='lines', line=dict(width=3)))
    fig_trains.update_layout(title="Active Trains per Loop", xaxis_title="Time of day", yaxis_title="Number of Trains", legend=dict(orientation="h"))

    t_unit = int(min_h) // 2 if min_h else 30

    # Timetable: forward and backward departures across all loops, in seconds
    table = []
    for loop_idx, (x_f, x_b) in enumerate(zip(x_scheduled, x1_scheduled)):
        for t in schedule_to_departures(x_f, t_unit):
            table.append({"direction": f"Forward (loop {loop_idx})",  "departure": t})
        for t in schedule_to_departures(x_b, t_unit):
            table.append({"direction": f"Backward (loop {loop_idx})", "departure": t})
    table.sort(key=lambda r: r["departure"])

    schedule_store = {"x_forward": [list(s) for s in x_scheduled],
                      "x_backward": [list(s) for s in x1_scheduled],
                      "t_unit": t_unit}

    return table, fig_passengers, fig_trains, schedule_store

@app.callback(
    Output("download-schedule-csv", "data"),
    Input("tab2-export-csv", "n_clicks"),
    State("tab2-schedule-store", "data"),
    prevent_initial_call=True,
)
def export_schedule_csv(n, schedule_data):
    if not schedule_data:
        return no_update
    import io, csv, zipfile as zf

    t_unit = schedule_data.get("t_unit", 30)
    x_forward  = schedule_data["x_forward"]
    x_backward = schedule_data["x_backward"]
    n_loops = len(x_forward)

    def make_single_csv(schedule):
        departures = schedule_to_departures(schedule, t_unit)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["departure_sec"])
        for d in departures:
            writer.writerow([d])
        return buf.getvalue().encode()

    zip_buf = io.BytesIO()
    with zf.ZipFile(zip_buf, "w", zf.ZIP_DEFLATED) as arc:
        if n_loops == 1:
            arc.writestr("schedule_forward.csv",  make_single_csv(x_forward[0]))
            arc.writestr("schedule_backward.csv", make_single_csv(x_backward[0]))
        else:
            for i in range(n_loops):
                arc.writestr(f"schedule_forward_loop_{i}.csv",  make_single_csv(x_forward[i]))
                arc.writestr(f"schedule_backward_loop_{i}.csv", make_single_csv(x_backward[i]))
    return dcc.send_bytes(zip_buf.getvalue(), "schedule.zip")


@app.callback(
    Output("download-analytics-pdf", "data"),
    Input("tab1-export-pdf", "n_clicks"),
    State("main-graph", "figure"),
    State("graph-dropdown", "value"),
    State("start-date", "date"),
    State("end-date", "date"),
    State("day-dropdown", "value"),
    State("month-dropdown", "value"),
    State("year-dropdown", "value"),
    State("stations-dropdown", "value"),
    State("excluded-dates-input", "value"),
    State("exceptions-store", "data"),
    State("hour-zero-input", "value"),
    State("illegal-boarding-rate-input", "value"),
    State("special-event-duration-input", "value"),
    State("analytics-load-folder", "value"),
    State("analytics-save-folder", "value"),
    prevent_initial_call=True
)
def export_tab1_pdf(n, fig, graph_type, start_date, end_date, day, month, year,
                    stations, excluded_dates, exceptions, hour_zero,
                    illegal_boarding_rate, special_event_duration,
                    load_folder, save_folder):
    graph_label = _GRAPH_LABEL.get(graph_type, graph_type) if graph_type else "—"

    _WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    _MONTHS   = {-1: "All", 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                  7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}

    exception_strs = []
    for row in (exceptions or []):
        if row.get("date"):
            try:
                d = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
                exception_strs.append(f"{d} (h{row.get('start_hour', 0)})")
            except (ValueError, TypeError):
                pass

    params = {
        "Graph type":             graph_label,
        "Date from":              start_date or "—",
        "Date to":                end_date or "—",
        "Day of week":            _WEEKDAYS[day] if day is not None else "—",
        "Month":                  _MONTHS.get(month, str(month)) if month is not None else "—",
        "Year":                   str(year) if year is not None else "—",
        "Station(s)":             ", ".join(stations) if stations else "All",
        "Excluded dates":         excluded_dates or "—",
        "Event dates":            ", ".join(exception_strs) if exception_strs else "—",
        "Hour zero":              str(hour_zero) if hour_zero is not None else "4",
        "Illegal boarding rate":  str(illegal_boarding_rate) if illegal_boarding_rate is not None else "0.1",
        "Special event duration": f"{special_event_duration} h" if special_event_duration is not None else "—",
        "Load folder":            load_folder or "—",
        "Save folder":            save_folder or "—",
    }

    return dcc.send_bytes(
        generate_pdf_report(fig, title=f"{graph_label} — 2-minute demand", params=params),
        "analytics_report.pdf",
    )

@app.callback(
    Output("download-schedule-pdf", "data"),
    Input("tab2-export-pdf", "n_clicks"),
    State("tab2-supply-demand-graph", "figure"),
    State("tab2-schedule-table", "data"),
    prevent_initial_call=True
)
def export_tab2_pdf(n, fig, table):
    return dcc.send_bytes(generate_pdf_report(fig, table, "Scheduling Report"), "schedule_report.pdf")


@app.callback(
    Output("download-metrics-pdf", "data"),
    Input("export-metrics-pdf-button", "n_clicks"),
    State("quality-unmatched-entries-graph", "figure"),
    State("quality-unmatched-exits-graph", "figure"),
    State("quality-same-station-graph", "figure"),
    State("quality-duplicates-graph", "figure"),
    State("quality-almost-duplicates-graph", "figure"),
    State("quality-category-entries-graph", "figure"),
    State("quality-category-exits-graph", "figure"),
    prevent_initial_call=True,
)
def export_metrics_pdf(n, fig_ue, fig_ux, fig_ss, fig_du, fig_ad, fig_ce, fig_cx):
    figs = [f for f in [fig_ue, fig_ux, fig_ss, fig_du, fig_ad, fig_ce, fig_cx]
            if f and f.get("data")]
    if not figs:
        return no_update
    return dcc.send_bytes(
        generate_metrics_pdf_report(figs, title="Processing Quality Metrics"),
        "metrics_report.pdf",
    )
@app.callback(
    Output("quality-metrics-store", "data"),
    Output("quality-metrics-status", "children"),
    Output("quality-scalars-display", "children"),
    Output("quality-unmatched-entries-graph", "figure"),
    Output("quality-unmatched-exits-graph", "figure"),
    Output("quality-same-station-graph", "figure"),
    Output("quality-duplicates-graph", "figure"),
    Output("quality-almost-duplicates-graph", "figure"),
    Input("load-quality-metrics-button", "n_clicks"),
    State("quality-date-from", "date"),
    State("quality-date-to", "date"),
    State("quality-load-folder", "value"),
    prevent_initial_call=True,
)
def load_quality_metrics(n_clicks, date_from_str, date_to_str, load_folder):
    empty_fig = {"data": [], "layout": {"template": "plotly_white"}}
    if not date_from_str or not date_to_str or not load_folder:
        return no_update, "Please fill in date range and load folder.", no_update, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig

    try:
        date_from = datetime.strptime(date_from_str, "%Y-%m-%d")
        date_to   = datetime.strptime(date_to_str,   "%Y-%m-%d")

        (inv_date, inv_bc, inv_id, inv_disc, inv_sta,
         unmatched_entries, unmatched_exits,
         cat_entries, cat_exits,
         same_station, duplicates, almost_dups) = display_extra_info(date_from, date_to, load_folder)

        store_data = {
            "cat_entries": np.array(cat_entries).tolist(),
            "cat_exits":   np.array(cat_exits).tolist(),
        }

        def _card(label, value):
            return html.Div(
                [
                    html.Div(f"{float(value):.1f}", style={"fontSize": "28px", "fontWeight": "bold", "color": "#8a1550"}),
                    html.Div(label, style={"fontSize": "12px", "color": "#555"}),
                ],
                style={
                    "border": "1px solid #eedde5", "borderRadius": "8px",
                    "padding": "14px 20px", "minWidth": "140px", "textAlign": "center",
                    "backgroundColor": "white", "boxShadow": "0 2px 4px rgba(138,21,80,0.08)",
                },
            )

        scalars_div = html.Div(
            [
                _card("Invalid dates",          inv_date),
                _card("Invalid boarding codes", inv_bc),
                _card("Invalid IDs",            inv_id),
                _card("Invalid discount codes", inv_disc),
                _card("Invalid stations",       inv_sta),
            ],
            style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "16px"},
        )

        bar_color = "#8a1550"
        axis_cfg  = {
            "tickangle": -90,
            "tickfont": {"size": 7},
            "tickmode": "linear",
            "automargin": True,
        }

        def _bar(x, y, title):
            fig = go.Figure(go.Bar(x=x, y=[float(v) for v in y], marker_color=bar_color))
            fig.update_layout(title=title, xaxis=axis_cfg, template="plotly_white", margin={"t": 50, "b": 160})
            return fig

        fig_ue = _bar(ALL_STATIONS, unmatched_entries, "Unmatched Entries per Station (avg/day)")
        fig_ux = _bar(ALL_STATIONS, unmatched_exits,   "Unmatched Exits per Station (avg/day)")
        fig_ss = _bar(ALL_STATIONS, same_station,      "Same-Station Tracks per Station (avg/day)")
        fig_du = _bar(ALL_STATIONS, duplicates,        "Duplicates per Station (avg/day)")
        fig_ad = _bar(ALL_STATIONS, almost_dups,       "Almost-Duplicates per Station (avg/day)")

        return store_data, "Metrics loaded successfully.", scalars_div, fig_ue, fig_ux, fig_ss, fig_du, fig_ad

    except Exception as e:
        empty_err = {"data": [], "layout": {"title": f"Error: {e}"}}
        return no_update, f"Error: {e}", no_update, empty_err, empty_err, empty_err, empty_err, empty_err


@app.callback(
    Output("quality-category-entries-graph", "figure"),
    Output("quality-category-exits-graph", "figure"),
    Input("quality-station-dropdown", "value"),
    State("quality-metrics-store", "data"),
    prevent_initial_call=True,
)
def update_category_charts(station_idx, store_data):
    empty = {"data": [], "layout": {"template": "plotly_white"}}
    if station_idx is None or not store_data:
        return empty, empty

    cat_entries = np.array(store_data["cat_entries"])
    cat_exits   = np.array(store_data["cat_exits"])
    station_name = ALL_STATIONS[station_idx]
    bar_color    = "#8a1550"
    axis_cfg     = {"tickangle": -30, "tickfont": {"size": 9}}

    fig_e = go.Figure(go.Bar(x=DISC_PROFILES, y=[float(v) for v in cat_entries[station_idx]], marker_color=bar_color))
    fig_e.update_layout(title=f"Category Entries — {station_name}", xaxis=axis_cfg, template="plotly_white", margin={"t": 50, "b": 100})

    fig_x = go.Figure(go.Bar(x=DISC_PROFILES, y=[float(v) for v in cat_exits[station_idx]], marker_color=bar_color))
    fig_x.update_layout(title=f"Category Exits — {station_name}", xaxis=axis_cfg, template="plotly_white", margin={"t": 50, "b": 100})

    return fig_e, fig_x


def _parse_csv_departures(contents, filename):
    """Decode a base64 Upload content and return a flat list of integer departure seconds."""
    import base64, csv as _csv
    if not contents:
        return []
    try:
        _header, encoded = contents.split(",", 1)
        decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
        reader = _csv.reader(decoded.splitlines())
        values = []
        for i, row in enumerate(reader):
            if i == 0:
                # Skip header row if all cells are non-numeric
                try:
                    [int(c) for c in row if c.strip()]
                except ValueError:
                    continue
            for cell in row:
                cell = cell.strip()
                if cell:
                    try:
                        values.append(int(cell))
                    except ValueError:
                        pass
        return values
    except Exception:
        return []


# Show filename after upload for each of the 6 slots
_UPLOAD_IDS = [
    "synt-upload-red-anthoupoli",
    "synt-upload-red-elliniko",
    "synt-upload-blue-dt1",
    "synt-upload-blue-doukissis",
    "synt-upload-blue-dt2",
    "synt-upload-blue-aerodromio",
]

for _uid in _UPLOAD_IDS:
    @app.callback(
        Output(f"{_uid}-name", "children"),
        Input(_uid, "filename"),
    )
    def _show_filename(filename, uid=_uid):
        return filename or ""


@app.callback(
    Output("syntagma-arrivals-graph", "figure"),
    Input("run-syntagma-button", "n_clicks"),
    State("synt-upload-red-anthoupoli",  "contents"),
    State("synt-upload-red-anthoupoli",  "filename"),
    State("synt-upload-red-elliniko",    "contents"),
    State("synt-upload-red-elliniko",    "filename"),
    State("synt-upload-blue-dt1",        "contents"),
    State("synt-upload-blue-dt1",        "filename"),
    State("synt-upload-blue-doukissis",  "contents"),
    State("synt-upload-blue-doukissis",  "filename"),
    State("synt-upload-blue-dt2",        "contents"),
    State("synt-upload-blue-dt2",        "filename"),
    State("synt-upload-blue-aerodromio", "contents"),
    State("synt-upload-blue-aerodromio", "filename"),
    State("synt-bin-size",               "value"),
    prevent_initial_call=True,
)
def run_syntagma_analysis(
    n_clicks,
    c_ra, f_ra, c_re, f_re,
    c_bd1, f_bd1, c_bd, f_bd,
    c_bd2, f_bd2, c_ba, f_ba,
    bin_size,
):
    try:
        sched_ra  = _parse_csv_departures(c_ra,  f_ra)
        sched_re  = _parse_csv_departures(c_re,  f_re)
        sched_bd1 = _parse_csv_departures(c_bd1, f_bd1)
        sched_bd  = _parse_csv_departures(c_bd,  f_bd)
        sched_bd2 = _parse_csv_departures(c_bd2, f_bd2)
        sched_ba  = _parse_csv_departures(c_ba,  f_ba)

        arrivals_red, arrivals_blue = find_syntagma_arrivals(
            sched_ra, sched_re,
            sched_bd1, sched_bd,
            sched_bd2, sched_ba,
        )

        # Aggregate into user-specified bins.
        # arrivals_* is indexed in seconds from midnight; service starts at 04:00.
        BIN = int(bin_size) if bin_size and int(bin_size) > 0 else 300
        SYNT_START = 4 * 3600  # 04:00 in seconds from midnight
        n_bins = len(arrivals_red) // BIN
        red_binned  = [float(np.sum(arrivals_red [i * BIN:(i + 1) * BIN])) for i in range(n_bins)]
        blue_binned = [float(np.sum(arrivals_blue[i * BIN:(i + 1) * BIN])) for i in range(n_bins)]
        x_labels = [
            f"{(((SYNT_START + i * BIN) // 3600) % 24):02d}:{((SYNT_START + i * BIN) % 3600) // 60:02d}"
            for i in range(n_bins)
        ]

        # Single stacked bar chart: each bin's bar is split red/blue.
        # A bin with 1 red + 1 blue arrival shows height 2, half red / half blue.
        fig = go.Figure()
        fig.add_trace(go.Bar(x=x_labels, y=red_binned,  name="Red line",  marker_color="#c0392b"))
        fig.add_trace(go.Bar(x=x_labels, y=blue_binned, name="Blue line", marker_color="#2980b9"))
        fig.update_layout(
            barmode="stack",
            height=500,
            showlegend=True,
            template="plotly_white",
            title="Arrivals at Syntagma",
            xaxis_title="Time of day (HH:MM)",
            yaxis_title=f"Trains per {BIN} s",
        )
        return fig

    except Exception as e:
        return {"data": [], "layout": {"title": f"Error: {e}"}}


@app.callback(
    Output("file-browser-modal", "style"),
    Output("file-browser-checklist", "options"),
    Output("file-browser-status", "children"),
    Input("download-analytics-files-btn", "n_clicks"),
    Input("file-browser-close-btn", "n_clicks"),
    State("analytics-save-folder", "value"),
    prevent_initial_call=True,
)
def toggle_file_browser(open_clicks, close_clicks, save_folder):
    _OVERLAY = {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "width": "100vw",
        "height": "100vh",
        "backgroundColor": "rgba(0,0,0,0.45)",
        "zIndex": 1000,
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    }
    _HIDDEN = {"display": "none"}

    if callback_context.triggered_id == "file-browser-close-btn":
        return _HIDDEN, no_update, no_update

    if not save_folder:
        return _OVERLAY, [], "No Analytics save folder specified."

    folder = Path(save_folder)
    if not folder.exists() or not folder.is_dir():
        return _OVERLAY, [], f"Folder not found: {save_folder}"

    files = sorted(f for f in folder.rglob('*') if f.is_file())
    options = [{"label": str(f.relative_to(folder)), "value": str(f)} for f in files]
    status = f"{len(files)} file(s) found in {save_folder}"
    return _OVERLAY, options, status


@app.callback(
    Output("download-analytics-files", "data"),
    Input("file-browser-download-btn", "n_clicks"),
    State("file-browser-checklist", "value"),
    prevent_initial_call=True,
)
def download_selected_files(n_clicks, selected):
    if not selected:
        return no_update
    import io as _io, zipfile as _zf
    buf = _io.BytesIO()
    with _zf.ZipFile(buf, "w", _zf.ZIP_DEFLATED) as arc:
        for path_str in selected:
            p = Path(path_str)
            if p.exists() and p.is_file():
                arc.write(p, arcname=p.name)
    return dcc.send_bytes(buf.getvalue(), "analytics_files.zip")


@app.callback(
    Output("download-training-csv", "data"),
    Output("training-status", "children"),
    Input("training-process-button", "n_clicks"),
    State("training-path-input", "value"),
    prevent_initial_call=True,
)
def run_processed_to_training(n_clicks, path):
    if not path or not path.strip():
        return no_update, "Please enter a path."
    try:
        df = processed_to_training(path.strip())
        return dcc.send_string(df.to_csv(index=False), "training_data.csv"), f"Done — {len(df)} rows exported."
    except Exception as e:
        return no_update, f"Error: {e}"


@app.callback(
    Output("download-ats-csv", "data"),
    Output("ats-status", "children"),
    Input("ats-process-button", "n_clicks"),
    State("ats-path-input", "value"),
    prevent_initial_call=True,
)
def run_process_ats(n_clicks, path):
    if not path or not path.strip():
        return no_update, "Please enter a path."
    try:
        df = process_ats(path.strip())
        return dcc.send_string(df.to_csv(index=False), "ats_data.csv"), f"Done — {len(df)} rows exported."
    except Exception as e:
        return no_update, f"Error: {e}"



if __name__ == "__main__":
    if __name__ == "__main__":
        app.run(
            host=params.HOST,
            port=params.PORT,
            debug=True,
        )