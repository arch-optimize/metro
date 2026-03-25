import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, input_size, horizon):
        """
        input_size: number of features per timestep
        horizon: number of timesteps to predict (e.g., 720 for short-term hourly, 365 for long-term daily)
        """
        super().__init__()

        self.horizon = horizon

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=128,
            num_layers=2,
            batch_first=True
        )

        self.dropout = nn.Dropout(0.2)
        self.fc = nn.Linear(128, horizon * 3)  # 3 lines

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # last timestep
        out = self.dropout(out)
        out = self.fc(out)
        return out