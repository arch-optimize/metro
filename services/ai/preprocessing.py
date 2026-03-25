import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

def load_and_preprocess(df, daily=False):
    df = df.copy()
    print("Columns before preprocessing:", df.columns.tolist())
    if "timestamp" not in df.columns:
        df["timestamp"] = pd.to_datetime(df[["year","month","day","hour"]])
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    if not daily:
        # Hourly features (short-term model)
        df["hour"] = df["timestamp"].dt.hour
        df["dow"] = df["timestamp"].dt.dayofweek
        df["month"] = df["timestamp"].dt.month

        df["hour_sin"] = np.sin(2*np.pi*df.hour/24)
        df["hour_cos"] = np.cos(2*np.pi*df.hour/24)
        df["dow_sin"] = np.sin(2*np.pi*df.dow/7)
        df["dow_cos"] = np.cos(2*np.pi*df.dow/7)
        df["month_sin"] = np.sin(2*np.pi*df.month/12)
        df["month_cos"] = np.cos(2*np.pi*df.month/12)
        df["weekend"] = (df["dow"] >= 5).astype(int)

        features = ["demand1","demand2","demand3","hour_sin","hour_cos",
                    "dow_sin","dow_cos","month_sin","month_cos","weekend"]
        data = df[features].values
    else:
        # Daily aggregation for long-term model

        daily_df = (
            df.groupby(df["timestamp"].dt.date)[["demand1", "demand2", "demand3"]]
            .sum()
            .reset_index()
        )

        # Rename properly
        daily_df.rename(columns={"timestamp": "date"}, inplace=True)

        # Create timestamp column cleanly
        daily_df["timestamp"] = pd.to_datetime(daily_df["date"])

        daily_df["day_of_year"] = daily_df["timestamp"].dt.dayofyear
        daily_df["day_sin"] = np.sin(2 * np.pi * daily_df.day_of_year / 365)
        daily_df["day_cos"] = np.cos(2 * np.pi * daily_df.day_of_year / 365)

        features = ["demand1", "demand2", "demand3", "day_sin", "day_cos"]
        data = daily_df[features].values
        df = daily_df


    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)

    return df, data_scaled, scaler