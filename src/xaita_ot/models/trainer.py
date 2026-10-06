from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from .cnn_lstm import CNNLSTM


class _CNNOnly(nn.Module):
    def __init__(self, n_features, channels=32, dropout=0.2):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(n_features, channels, kernel_size=3, padding=1),
            nn.ReLU(), nn.BatchNorm1d(channels), nn.Dropout(dropout)
        )
        self.head = nn.Sequential(nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Linear(channels, 1))

    def forward(self, x):
        return self.head(self.conv(x.transpose(1, 2))).squeeze(-1)


class _LSTMOnly(nn.Module):
    def __init__(self, n_features, hidden=64, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_features, hidden, batch_first=True)
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(hidden, 1))

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(out[:, -1]).squeeze(-1)


class Detector:
    def __init__(self, n_features: int, config, architecture="cnn_lstm"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if architecture == "cnn":
            self.model = _CNNOnly(n_features, config.cnn_channels, config.dropout).to(self.device)
        elif architecture == "lstm":
            self.model = _LSTMOnly(n_features, config.lstm_hidden, config.dropout).to(self.device)
        else:
            self.model = CNNLSTM(n_features, config.cnn_channels, config.lstm_hidden, config.dropout).to(self.device)
        self.architecture = architecture
        self.threshold = 0.5

    def fit(self, X, y, epochs=8, batch_size=128, lr=1e-3):
        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y, dtype=np.float32)
        if X.ndim != 3 or len(X) != len(y) or not len(X):
            raise ValueError("training data must be non-empty with shapes [N, T, F] and [N]")
        if not np.isfinite(X).all() or not np.isfinite(y).all():
            raise ValueError("training data must be finite")
        if not np.isin(y, [0.0, 1.0]).all():
            raise ValueError("training labels must be binary 0/1")
        if np.unique(y).size < 2:
            raise ValueError("training requires both normal (0) and attack (1) classes")
        if epochs <= 0 or batch_size <= 0 or lr <= 0:
            raise ValueError("epochs, batch_size and lr must be positive")
        ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
        loader = DataLoader(ds, batch_size=batch_size, shuffle=True)
        pos = int(y.sum()); neg = len(y) - pos
        weight = torch.tensor([neg / pos], device=self.device)
        loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=weight)
        opt = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)
        self.model.train()
        for _ in range(epochs):
            for xb, yb in loader:
                xb, yb = xb.to(self.device), yb.to(self.device)
                opt.zero_grad(set_to_none=True)
                loss = loss_fn(self.model(xb), yb)
                loss.backward(); torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0); opt.step()
        return self

    @torch.no_grad()
    def predict_proba(self, X):
        self.model.eval(); logits = []
        for i in range(0, len(X), 1024):
            xb = torch.from_numpy(np.asarray(X[i:i + 1024]).copy()).to(self.device)
            logits.append(torch.sigmoid(self.model(xb)).cpu().numpy())
        return np.concatenate(logits) if logits else np.array([])

    def evaluate(self, X, y):
        X = np.asarray(X, dtype=np.float32)
        y = np.asarray(y).astype(int)
        if len(X) != len(y) or not np.isfinite(X).all():
            raise ValueError("evaluation data must be aligned and finite")
        p = self.predict_proba(X); pred = (p >= self.threshold).astype(int)
        pr, re, f1, _ = precision_recall_fscore_support(y, pred, average='binary', zero_division=0)
        auc = roc_auc_score(y, p) if len(np.unique(y)) > 1 else float('nan')
        fp = ((pred == 1) & (y == 0)).sum(); tn = ((pred == 0) & (y == 0)).sum()
        return {'precision': float(pr), 'recall': float(re), 'f1': float(f1), 'fpr': float(fp / max(1, fp + tn)), 'auroc': float(auc)}

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({'state_dict': self.model.state_dict(), 'threshold': self.threshold, 'architecture': self.architecture}, path)

    def load(self, path):
        obj = torch.load(path, map_location=self.device, weights_only=False)
        if not isinstance(obj, dict) or not isinstance(obj.get('state_dict'), dict):
            raise ValueError("invalid detector checkpoint")
        threshold = float(obj.get('threshold', 0.5))
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("checkpoint threshold must be in [0, 1]")
        architecture = obj.get('architecture')
        if architecture is not None and architecture != self.architecture:
            raise ValueError(f"checkpoint architecture '{architecture}' does not match '{self.architecture}'")
        self.model.load_state_dict(obj['state_dict'])
        self.threshold = threshold
        return self
