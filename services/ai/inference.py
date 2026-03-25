import torch
import numpy as np
import pandas as pd

from services.ai.model import LSTMModel
from services.ai.preprocessing import load_and_preprocess
from services.ai.config import *
from services.ai.dataset import create_sequences

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def inverse_scale(values, scaler, num_features):
    samples, horizon, lines = values.shape

    dummy = np.zeros((samples * horizon, num_features))
    dummy[:, :3] = values.reshape(-1, 3)

    inv = scaler.inverse_transform(dummy)
    return inv[:, :3].reshape(samples, horizon, 3)


def run_inference(df, start_date, start_hour, model_type="short"):
    print("Starting inference...")

    # -----------------------------------
    # Select config based on model type
    # -----------------------------------
    if model_type == "short":
        horizon = SHORT_HORIZON
        model_path = SHORT_MODEL_PATH
        daily = False
    else:
        horizon = LONG_HORIZON
        model_path = LONG_MODEL_PATH
        daily = True

    # -----------------------------------
    # Preprocess
    # -----------------------------------
    df_proc, data_scaled, scaler = load_and_preprocess(df, daily=daily)

    # -----------------------------------
    # Build timestamp
    # -----------------------------------
    start_ts = pd.to_datetime(start_date)

    if not daily:
        start_ts = start_ts + pd.Timedelta(hours=start_hour)

    # -----------------------------------
    # Find index
    # -----------------------------------
    idx = df_proc[df_proc["timestamp"] == start_ts].index

    if len(idx) == 0:
        raise ValueError("Selected timestamp not found in dataset")

    idx = idx[0]

    if idx < LOOKBACK:
        raise ValueError("Not enough history before selected date")

    # -----------------------------------
    # Build input sequence
    # -----------------------------------
    X_input = data_scaled[idx - LOOKBACK: idx]
    X_input = np.expand_dims(X_input, axis=0)

    X_tensor = torch.tensor(X_input, dtype=torch.float32).to(DEVICE)

    # -----------------------------------
    # Load model
    # -----------------------------------
    model = LSTMModel(
        input_size=X_input.shape[2],
        horizon=horizon
    ).to(DEVICE)
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.eval()

    # -----------------------------------
    # Predict
    # -----------------------------------
    with torch.no_grad():
        pred = model(X_tensor).cpu().numpy()

    pred = pred.reshape(1, horizon, 3)

    # -----------------------------------
    # Inverse scale
    # -----------------------------------
    pred = inverse_scale(pred, scaler, data_scaled.shape[1])[0]

    # -----------------------------------
    # Build output dataframe
    # -----------------------------------
    if daily:
        timestamps = pd.date_range(start=start_ts, periods=horizon, freq="D")
    else:
        timestamps = pd.date_range(start=start_ts, periods=horizon, freq="h")

    forecast_df = pd.DataFrame({
        "timestamp": timestamps,
        "demand1": pred[:, 0],
        "demand2": pred[:, 1],
        "demand3": pred[:, 2],
    })

    return forecast_df