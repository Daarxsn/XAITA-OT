import torch
from torch import nn

class CNNLSTM(nn.Module):
    def __init__(self, n_features: int, cnn_channels: int = 32, hidden: int = 64, dropout: float = 0.2):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(n_features, cnn_channels, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(cnn_channels),
            nn.Dropout(dropout),
        )
        self.lstm = nn.LSTM(cnn_channels, hidden, batch_first=True)
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(hidden, 1))

    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.conv(x).transpose(1, 2)
        out, _ = self.lstm(x)
        return self.head(out[:, -1]).squeeze(-1)
