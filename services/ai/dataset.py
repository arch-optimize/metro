import numpy as np

def create_sequences(data, lookback, horizon):
    """
    data: scaled array (n_samples, n_features)
    lookback: number of past timesteps to use for X
    horizon: number of future timesteps to predict
    """

    X = []
    y = []

    for i in range(len(data) - lookback - horizon):
        X.append(data[i:i + lookback])
        y.append(data[i + lookback:i + lookback + horizon, :3])  # first 3 columns = demand lines

    X = np.array(X)
    y = np.array(y)

    y = y.reshape(len(y), horizon * 3)  # flatten to (samples, horizon*3)

    return X, y