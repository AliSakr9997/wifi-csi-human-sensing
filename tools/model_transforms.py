"""Persisted training-time centering, scaling, and PCA for inference."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

class FittedCSITransform:
    def __init__(self, mean, scale, components, active_mask=None, metadata=None):
        self.mean = np.asarray(mean, dtype=np.float32)
        self.scale = np.asarray(scale, dtype=np.float32)
        self.components = np.asarray(components, dtype=np.float32)
        self.active_mask = None if active_mask is None else np.asarray(active_mask, dtype=bool)
        self.metadata = metadata or {}

    @classmethod
    def fit(cls, data, n_components=3, active_mask=None, metadata=None):
        values = np.asarray(data, dtype=np.float32)
        mean = values.mean(axis=0)
        scale = values.std(axis=0)
        scale[scale == 0] = 1.0
        normalized = (values - mean) / scale
        _, _, vectors = np.linalg.svd(normalized, full_matrices=False)
        return cls(mean, scale, vectors[:n_components], active_mask, metadata)

    def transform(self, data):
        values = np.asarray(data, dtype=np.float32)
        if values.shape[1] != self.mean.size:
            raise ValueError(f"expected {self.mean.size} channels, got {values.shape[1]}")
        return ((values - self.mean) / self.scale) @ self.components.T

    def save(self, path):
        path = Path(path)
        np.savez(path, mean=self.mean, scale=self.scale, components=self.components, active_mask=self.active_mask if self.active_mask is not None else np.array([], dtype=bool), metadata=np.array(json.dumps(self.metadata)))

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as values:
            mask = values['active_mask']
            metadata = json.loads(str(values['metadata'].item()))
            return cls(values['mean'], values['scale'], values['components'], mask if mask.size else None, metadata)
