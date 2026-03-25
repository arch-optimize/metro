import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from config import *
from model import LSTMModel
from preprocessing import load_and_preprocess
from dataset import create_sequences


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# -------------------------------------------------
# INVERSE SCALING FUNCTION
# -------------------------------------------------

def inverse_scale_demand(values, scaler):

    samples, horizon, lines = values.shape

    dummy = np.zeros((samples * horizon, 10))

    dummy[:, :3] = values.reshape(-1, 3)

    inv = scaler.inverse_transform(dummy)

    return inv[:, :3].reshape(samples, horizon, 3)


# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------

print("Loading dataset...")

df, data_scaled, scaler = load_and_preprocess(DATA_PATH)

X, y = create_sequences(data_scaled)

split = int(len(X) * 0.8)

X_test = X[split:]
y_test = y[split:]

X_test_tensor = torch.tensor(X_test, dtype=torch.float32).to(DEVICE)


# -------------------------------------------------
# LOAD MODEL
# -------------------------------------------------

print("Loading trained model...")

model = LSTMModel(input_size=X.shape[2]).to(DEVICE)

model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))

model.eval()


# -------------------------------------------------
# PREDICTIONS
# -------------------------------------------------

print("Running predictions...")

with torch.no_grad():
    pred = model(X_test_tensor)

pred = pred.cpu().numpy()

pred = pred.reshape(len(pred), HORIZON, 3)
y_test = y_test.reshape(len(y_test), HORIZON, 3)


# -------------------------------------------------
# INVERSE SCALE DEMAND
# -------------------------------------------------

pred = inverse_scale_demand(pred, scaler)
y_test = inverse_scale_demand(y_test, scaler)


# -------------------------------------------------
# METRICS
# -------------------------------------------------

metrics = []

for line in range(3):

    y_true = y_test[:, :, line].flatten()
    y_pred = pred[:, :, line].flatten()

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    # MAPE-based accuracy
    mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-6)))
    accuracy = (1 - mape) * 100

    metrics.append([mse, rmse, mae, r2, accuracy])

metrics_df = pd.DataFrame(
    metrics,
    columns=["MSE", "RMSE", "MAE", "R2", "Accuracy (%)"],
    index=["Line1", "Line2", "Line3"]
)

print("\nEvaluation Metrics\n")
print(metrics_df.round(3))


# -------------------------------------------------
# QUALITATIVE FORECAST PLOTS
# -------------------------------------------------

sample = 5

actual = y_test[sample]
forecast = pred[sample]

line_names = ["Line 1", "Line 2", "Line 3"]
pred_colors = ["green", "red", "blue"]

# build timestamp axis
start_idx = split + sample + LOOKBACK
timestamps = df["timestamp"].iloc[start_idx:start_idx + HORIZON]

# daily tick positions
tick_positions = np.arange(0, HORIZON, 24)

tick_labels = [
    f"{timestamps.iloc[i].month}/{timestamps.iloc[i].day}/{str(timestamps.iloc[i].year)[2:]}"
    for i in tick_positions
]

for i in range(3):

    plt.figure(figsize=(14,6))

    plt.plot(
        actual[:, i],
        label="Actual",
        color="black",
        linewidth=2.5
    )

    plt.plot(
        forecast[:, i],
        linestyle="--",
        label="Predicted",
        color=pred_colors[i],
        linewidth=2.5
    )

    plt.title(f"Actual vs Predicted Demand ({line_names[i]})", fontsize=18)

    plt.xlabel("Date", fontsize=14)
    plt.ylabel("Passenger Demand", fontsize=14)

    plt.xticks(
        tick_positions,
        tick_labels,
        rotation=45,
        fontsize=12
    )

    plt.yticks(fontsize=12)

    plt.legend(fontsize=13)

    plt.grid(True)

    plt.tight_layout()

    plt.show()