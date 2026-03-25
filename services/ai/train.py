import torch
from torch.utils.data import DataLoader, Dataset
import torch.nn as nn

from services.ai.model import LSTMModel
from services.ai.dataset import create_sequences
from services.ai.preprocessing import load_and_preprocess
from services.ai.config import *

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# -----------------------------
# Dataset wrapper
# -----------------------------
class DemandDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# -----------------------------
# Generic training function
# -----------------------------
def train_single_model(df, horizon, model_path, daily=False):
    print(f"\nTraining model -> horizon={horizon}, daily={daily}")

    # Preprocess
    _, data_scaled, scaler = load_and_preprocess(df, daily=daily)

    # Create sequences
    X, y = create_sequences(
        data_scaled,
        lookback=LOOKBACK,
        horizon=horizon
    )

    if len(X) == 0:
        raise ValueError("Not enough data for given LOOKBACK + HORIZON")

    # Train/test split
    split = int(len(X) * 0.8)

    train_dataset = DemandDataset(X[:split], y[:split])
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False
    )

    # Model
    model = LSTMModel(
        input_size=X.shape[2],
        horizon=horizon
    ).to(DEVICE)

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.SmoothL1Loss()

    # Training loop
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0

        for xb, yb in train_loader:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)

            optimizer.zero_grad()

            pred = model(xb)
            loss = criterion(pred, yb)

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        print(f"Epoch {epoch+1}/{EPOCHS} finished | Loss: {total_loss/len(train_loader):.6f}")

    # Save model
    torch.save(model.state_dict(), model_path)
    print(f"Model saved -> {model_path}")

    return model, scaler


# -----------------------------
# Train BOTH models
# -----------------------------
def train_both_models(df):
    """
    Trains:
    - Short-term model (hourly, 1 month)
    - Long-term model (daily, 1 year)
    """

    print("\n===== TRAINING SHORT-TERM MODEL =====")
    short_model, short_scaler = train_single_model(
        df=df,
        horizon=SHORT_HORIZON,
        model_path=SHORT_MODEL_PATH,
        daily=False
    )

    print("\n===== TRAINING LONG-TERM MODEL =====")
    long_model, long_scaler = train_single_model(
        df=df,
        horizon=LONG_HORIZON,
        model_path=LONG_MODEL_PATH,
        daily=True
    )

    print("\n✅ BOTH MODELS TRAINED SUCCESSFULLY")

    return {
        "short_model": short_model,
        "short_scaler": short_scaler,
        "long_model": long_model,
        "long_scaler": long_scaler
    }