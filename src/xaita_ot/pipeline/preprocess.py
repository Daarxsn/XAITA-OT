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
    assets: np.ndarray
    protocols: np.ndarray
    sources: np.ndarray
    destinations: np.ndarray


class OTPreprocessor:
    def __init__(self, window_size: int = 32):
        self.window_size = window_size
        self.scaler = StandardScaler()
        self.feature_names: list[str] = []
        self.fill_values: dict[str, float] = {}

    def fit_transform_train(self, df: pd.DataFrame, label_col: str = "label") -> WindowedData:
        numeric = df.select_dtypes(include=[np.number]).copy()
        if label_col in numeric:
            numeric = numeric.drop(columns=[label_col])
        self.feature_names = list(numeric.columns)
        if not self.feature_names:
            raise ValueError("No numeric telemetry features found")
        self.fill_values = {
            column: float(numeric[column].median()) if pd.notna(numeric[column].median()) else 0.0
            for column in self.feature_names
        }
        X = self.scaler.fit_transform(numeric[self.feature_names].fillna(self.fill_values))
        y = df[label_col].astype(int).to_numpy() if label_col in df else np.zeros(len(df), dtype=int)
        return self._window(X, y, df)

    def transform(self, df: pd.DataFrame, label_col: str = "label") -> WindowedData:
        numeric = df.reindex(columns=self.feature_names, fill_value=0).select_dtypes(include=[np.number])
        X = self.scaler.transform(numeric[self.feature_names].fillna(self.fill_values))
        y = df[label_col].astype(int).to_numpy() if label_col in df else np.zeros(len(df), dtype=int)
        return self._window(X, y, df)

    def _window(self, X, y, df) -> WindowedData:
        if len(X) < self.window_size:
            raise ValueError(f"Need at least {self.window_size} rows, got {len(X)}")
        indices = range(self.window_size - 1, len(X))
        Xw = np.stack([X[i-self.window_size+1:i+1] for i in indices])
        yw = np.array([int(np.max(y[i-self.window_size+1:i+1]) > 0) for i in indices])
        start = self.window_size - 1
        timestamps = df["timestamp"].to_numpy()[start:]

        def column(name):
            if name in df:
                return df[name].astype(str).to_numpy()[start:]
            return np.full(len(Xw), "unknown")

        return WindowedData(
            Xw.astype(np.float32), yw, timestamps, self.feature_names,
            column("asset"), column("protocol"), column("src_ip"), column("dst_ip")
        )
