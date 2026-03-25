from dash import dcc, html, dash_table
from dash import Input, Output, State
import pandas as pd
import base64
import io
import plotly.graph_objs as go

from services.ai.train import train_both_models
from services.ai.inference import run_inference


# =====================================================
# UI
# =====================================================

def render_tab3():
    return html.Div(
        [
            html.H2("Tab 3 - Demand Prediction"),
            html.Hr(),

            # -----------------------------
            # 1️⃣ Upload CSV
            # -----------------------------
            html.H3("1. Upload processed dataset"),
            dcc.Upload(
                id="upload-csv-tab3",
                children=html.Div(
                    "Drag and drop or click to upload a historical demand CSV (.csv)"
                ),
                multiple=False,
                style={
                    "width": "100%",
                    "height": "70px",
                    "lineHeight": "70px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "8px",
                    "textAlign": "center",
                    "marginBottom": "12px",
                },
            ),
            html.Div(id="tab3-upload-status", style={"marginBottom": "20px"}),

            dcc.Store(id="tab3-df-store"),

            html.Hr(),

            # -----------------------------
            # 2️⃣ Prediction settings
            # -----------------------------
            html.H3("2. Prediction settings"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Prediction start date"),
                            dcc.DatePickerSingle(
                                id="tab3-date",
                                display_format="YYYY-MM-DD",
                            ),
                            dcc.Input(
                                id="tab3-hour",
                                type="number",
                                min=0,
                                max=23,
                                step=1,
                                placeholder="Hour (0-23)",
                                style={"width": "100%", "marginTop": "6px"},
                            ),
                        ],
                        style={"width": "30%", "display": "inline-block", "marginRight": "4%"},
                    ),
                    html.Div(
                        [
                            html.Label("Prediction horizon"),
                            dcc.Dropdown(
                                id="tab3-horizon",
                                options=[
                                    {"label": "Short-term (1 month hourly)", "value": "short"},
                                    {"label": "Long-term (1 year daily)", "value": "long"},
                                ],
                                value="short",
                                clearable=False,
                            ),
                        ],
                        style={"width": "30%", "display": "inline-block"},
                    ),
                ],
                style={"marginBottom": "25px"},
            ),

            html.Hr(),

            # -----------------------------
            # 3️⃣ Actions
            # -----------------------------
            html.H3("3. Actions"),
            html.Div(
                [
                    html.Button(
                        "Run prediction",
                        id="tab3-run-prediction",
                        n_clicks=0,
                        className="button-primary",
                        style={"width": "160px", "height": "40px", "marginRight": "10px"},
                    ),
                    html.Button(
                        "Train models",
                        id="tab3-retrain-model",
                        n_clicks=0,
                        style={
                            "width": "160px",
                            "height": "40px",
                            "backgroundColor": "#8a1550",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "5px",
                        },
                    ),
                    html.Button(
                        "Download Predictions CSV",
                        id="tab3-download-btn",
                        n_clicks=0,
                        style={
                            "width": "180px",
                            "height": "40px",
                            "backgroundColor": "#8a1550",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "5px",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                },
            ),

            dcc.Loading(
                type="circle",
                children=[
                    html.Div(
                        id="tab3-prediction-status",
                        children="Select settings and choose an action.",
                        style={"marginTop": "12px", "marginBottom": "12px"},
                    ),
                ],
            ),

            html.Hr(),

            # -----------------------------
            # 4️⃣ Results
            # -----------------------------
            html.H3("4. Prediction results"),
            dcc.Graph(id="tab3-demand-forecast-graph"),

            html.Br(),

            dash_table.DataTable(
                id="tab3-metrics-table",
                columns=[
                    {"name": "Metric", "id": "metric"},
                    {"name": "Value", "id": "value"},
                ],
                data=[],
                page_size=10,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": "#8a1550",
                    "color": "white",
                    "fontWeight": "bold",
                    "textAlign": "center",
                },
            ),

            dcc.Download(id="tab3-download"),
        ],
        style={"padding": "12px"},
    )


# =====================================================
# CALLBACKS
# =====================================================

def register_tab3_callbacks(app):

    # -----------------------------
    # Upload CSV
    # -----------------------------
    @app.callback(
        Output("tab3-upload-status", "children"),
        Output("tab3-df-store", "data"),
        Input("upload-csv-tab3", "contents"),
        State("upload-csv-tab3", "filename"),
        prevent_initial_call=True,
    )
    def handle_upload(contents, filename):
        if not contents:
            return "No file uploaded.", None

        try:
            _, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))

            return (
                f"Upload successful: {filename} — {df.shape[0]} rows",
                df.to_json(date_format="iso", orient="split"),
            )

        except Exception as e:
            return f"Upload failed: {e}", None

    # -----------------------------
    # Train models
    # -----------------------------
    @app.callback(
        Output("tab3-prediction-status", "children"),
        Input("tab3-retrain-model", "n_clicks"),
        State("tab3-df-store", "data"),
        prevent_initial_call=True,
    )
    def retrain_models(n_clicks, df_json):
        if not df_json:
            return "No dataset uploaded."

        try:
            df = pd.read_json(io.StringIO(df_json), orient="split")

            train_both_models(df)

            return "Both models trained successfully ✅ (check backend logs)"

        except Exception as e:
            print("TRAIN ERROR:", e)
            return f"Training failed: {str(e)}"

    # -----------------------------
    # Run prediction
    # -----------------------------
    @app.callback(
        Output("tab3-demand-forecast-graph", "figure"),
        Output("tab3-metrics-table", "data"),
        Output("tab3-prediction-status", "children",allow_duplicate=True),
        Input("tab3-run-prediction", "n_clicks"),
        State("tab3-df-store", "data"),
        State("tab3-date", "date"),
        State("tab3-hour", "value"),
        State("tab3-horizon", "value"),
        prevent_initial_call=True,
    )
    def run_prediction(n_clicks, df_json, start_date, start_hour, horizon):

        if not df_json:
            return {}, [], "No dataset uploaded."

        if not start_date:
            return {}, [], "Please select a start date."

        try:
            df = pd.read_json(io.StringIO(df_json), orient="split")

            forecast_df = run_inference(
                df,
                start_date,
                start_hour,
                model_type=horizon
            )

            # -------- GRAPH --------
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=forecast_df["timestamp"],
                y=forecast_df["demand1"],
                name="Line 1",
                line=dict(color="green")
            ))

            fig.add_trace(go.Scatter(
                x=forecast_df["timestamp"],
                y=forecast_df["demand2"],
                name="Line 2",
                line=dict(color="red")
            ))

            fig.add_trace(go.Scatter(
                x=forecast_df["timestamp"],
                y=forecast_df["demand3"],
                name="Line 3",
                line=dict(color="blue")
            ))

            fig.update_layout(
                title="Demand Forecast",
                xaxis_title="Time",
                yaxis_title="Demand",
                template="plotly_white"
            )

            # -------- METRICS --------
            metrics = [
                {"metric": "Model", "value": horizon},
                {"metric": "Horizon length", "value": len(forecast_df)},
                {"metric": "Start", "value": str(forecast_df["timestamp"].iloc[0])},
                {"metric": "End", "value": str(forecast_df["timestamp"].iloc[-1])},
            ]

            return fig, metrics, "Prediction completed ✅"

        except Exception as e:
            print("PREDICTION ERROR:", e)
            return {}, [{"metric": "Error", "value": str(e)}], f"Error: {str(e)}"

    # -----------------------------
    # Download CSV
    # -----------------------------
    @app.callback(
        Output("tab3-download", "data"),
        Input("tab3-download-btn", "n_clicks"),
        State("tab3-df-store", "data"),
        State("tab3-date", "date"),
        State("tab3-hour", "value"),
        State("tab3-horizon", "value"),
        prevent_initial_call=True,
    )
    def download_csv(n_clicks, df_json, start_date, start_hour, horizon):

        if not df_json:
            return None

        df = pd.read_json(io.StringIO(df_json), orient="split")

        forecast_df = run_inference(df, start_date, start_hour, horizon)

        return dcc.send_data_frame(
            forecast_df.to_csv,
            "demand_forecast.csv",
            index=False
        )