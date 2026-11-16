"""Canonical CSI parsing and packet-timing validation helpers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class ParsedCSI:
    time: np.ndarray
    amplitudes: np.ndarray
    phases: np.ndarray
    records: pd.DataFrame

def parse_iq_payload(raw_data: Any) -> tuple[np.ndarray, np.ndarray]:
    """Decode interleaved IQ and remove the ESP32 first_word_invalid pair."""
    raw = str(raw_data).strip(' "[]')
    if not raw:
        raise ValueError("empty CSI payload")
    separator = ';' if ';' in raw else ','
    values = [int(value.strip()) for value in raw.split(separator) if value.strip()]
    if len(values) < 4 or len(values) % 2:
        raise ValueError("invalid CSI IQ payload")
    iq = np.asarray(values, dtype=np.float32).reshape(-1, 2)[1:]
    imaginary, real = iq[:, 0], iq[:, 1]
    return np.hypot(imaginary, real), np.arctan2(imaginary, real)

def parse_csi_records(df: pd.DataFrame) -> ParsedCSI:
    amplitudes, phases, indices = [], [], []
    for index, row in df.iterrows():
        try:
            amplitude, phase = parse_iq_payload(row['data'])
        except (KeyError, TypeError, ValueError):
            continue
        amplitudes.append(amplitude); phases.append(phase); indices.append(index)
    if not amplitudes:
        raise ValueError("no valid CSI rows found")
    records = df.loc[indices]
    timestamps = records['host_time'].to_numpy(dtype=np.float64)
    return ParsedCSI(timestamps - timestamps[0], np.asarray(amplitudes, dtype=np.float32), np.asarray(phases, dtype=np.float32), records)

def validate_packet_intervals(timestamps: np.ndarray, max_relative_jitter: float = 0.25, max_gap_factor: float = 2.5) -> float:
    """Validate timestamps and return 1 / median packet interval."""
    values = np.asarray(timestamps, dtype=np.float64)
    if values.size < 3:
        raise ValueError("at least three timestamps are required")
    intervals = np.diff(values)
    if np.any(intervals <= 0):
        raise ValueError("packet timestamps must be strictly increasing")
    median = float(np.median(intervals))
    jitter = float(np.median(np.abs(intervals - median)) / median)
    if jitter > max_relative_jitter or float(np.max(intervals)) > max_gap_factor * median:
        raise ValueError(f"inconsistent packet intervals: median={median:.6g}s, jitter={jitter:.3f}")
    return 1.0 / median

def load_csi(csv_path: str) -> ParsedCSI:
    parsed = parse_csi_records(pd.read_csv(csv_path, dtype={'data': str, 'mac': str}))
    validate_packet_intervals(parsed.time)
    return parsed
