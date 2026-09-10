from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler


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
    """Leakage-controlled numeric scaling + train-fitted categorical encoding."""

    CATEGORICAL_COLUMNS = ("asset", "protocol", "src_ip", "dst_ip")

    def __init__(self, window_size: int = 32):
        self.window_size = window_size
        self.scaler = StandardScaler()
        self.encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.numeric_features: list[str] = []
        self.categorical_features: list[str] = []
        self.feature_names: list[str] = []
        self.fill_values: dict[str, float] = {}
        self.encoder_fitted = False

    def fit_transform_train(self, df: pd.DataFrame, label_col: str = "label") -> WindowedData:
        numeric = df.select_dtypes(include=[np.number]).copy()
        if label_col in numeric:
            numeric = numeric.drop(columns=[label_col])
        self.numeric_features = list(numeric.columns)
        self.fill_values = {
            column: float(numeric[column].median()) if pd.notna(numeric[column].median()) else 0.0
            for column in self.numeric_features
        }
        numeric_x = self.scaler.fit_transform(numeric[self.numeric_features].fillna(self.fill_values)) if self.numeric_features else np.empty((len(df), 0))

        self.categorical_features = [c for c in self.CATEGORICAL_COLUMNS if c in df.columns]
        if self.categorical_features:
            categorical = df[self.categorical_features].fillna("unknown").astype(str)
            categorical_x = self.encoder.fit_transform(categorical)
            self.encoder_fitted = True
            encoded_names = list(self.encoder.get_feature_names_out(self.categorical_features))
        else:
            categorical_x = np.empty((len(df), 0))
            encoded_names = []
        self.feature_names = self.numeric_features + encoded_names
        if not self.feature_names:
            raise ValueError("No usable telemetry features found")
        X = np.concatenate([numeric_x, categorical_x], axis=1).astype(np.float32)
        y = df[label_col].astype(int).to_numpy() if label_col in df else np.zeros(len(df), dtype=int)
        return self._window(X, y, df)

    def transform(self, df: pd.DataFrame, label_col: str = "label") -> WindowedData:
        numeric = df.reindex(columns=self.numeric_features, fill_value=0).select_dtypes(include=[np.number])
        numeric_x = self.scaler.transform(numeric[self.numeric_features].fillna(self.fill_values)) if self.numeric_features else np.empty((len(df), 0))
        if self.encoder_fitted:
            categorical = df.reindex(columns=self.categorical_features, fill_value="unknown").fillna("unknown").astype(str)
            categorical_x = self.encoder.transform(categorical)
        else:
            categorical_x = np.empty((len(df), 0))
        X = np.concatenate([numeric_x, categorical_x], axis=1).astype(np.float32)
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
            Xw, yw, timestamps, self.feature_names,
            column("asset"), column("protocol"), column("src_ip"), column("dst_ip")
        )
