from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

@dataclass
class WindowedData:
    X: np.ndarray
    y: np.ndarray
    timestamps: np.ndarray
    feature_names: list[str]

class OTPreprocessor:
    def __init__(self, window_size: int = 32):
        self.window_size = window_size
        self.scaler = StandardScaler()
        self.feature_names: list[str] = []

    def fit_transform_train(self, df: pd.DataFrame, label_col: str = "label") -> WindowedData:
        numeric = df.select_dtypes(include=[np.number]).copy()
        if label_col in numeric:
            numeric = numeric.drop(columns=[label_col])
        self.feature_names = list(numeric.columns)
        if not self.feature_names:
            raise ValueError("No numeric telemetry features found")
        X = self.scaler.fit_transform(numeric.fillna(numeric.median()).fillna(0.0))
        y = df[label_col].astype(int).to_numpy() if label_col in df else np.zeros(len(df), dtype=int)
        return self._window(X, y, df["timestamp"].to_numpy())

    def transform(self, df: pd.DataFrame, label_col: str = "label") -> WindowedData:
        numeric = df.reindex(columns=self.feature_names, fill_value=0).select_dtypes(include=[np.number])
        X = self.scaler.transform(numeric.fillna(0.0))
        y = df[label_col].astype(int).to_numpy() if label_col in df else np.zeros(len(df), dtype=int)
        return self._window(X, y, df["timestamp"].to_numpy())

    def _window(self, X, y, ts) -> WindowedData:
        if len(X) < self.window_size:
            raise ValueError(f"Need at least {self.window_size} rows, got {len(X)}")
        Xw = np.stack([X[i-self.window_size+1:i+1] for i in range(self.window_size-1, len(X))])
        yw = np.array([int(np.max(y[i-self.window_size+1:i+1]) > 0) for i in range(self.window_size-1, len(X))])
        tw = np.array([ts[i] for i in range(self.window_size-1, len(X))])
        return WindowedData(Xw.astype(np.float32), yw, tw, self.feature_names)
