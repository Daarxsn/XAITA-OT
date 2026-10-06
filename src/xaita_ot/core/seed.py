import random

import numpy as np


def set_seed(seed: int = 42) -> None:
    """Seed Python, NumPy and the mandatory PyTorch dependency deterministically."""
    seed = int(seed)
    if seed < 0:
        raise ValueError("seed must be non-negative")
    random.seed(seed)
    np.random.seed(seed)
    import torch
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
