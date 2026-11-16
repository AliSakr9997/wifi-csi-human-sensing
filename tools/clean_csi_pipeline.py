"""Six-stage CSI cleaning pipeline with canonical ingestion and timing checks."""
import os
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
from csi_processing import load_csi, validate_packet_intervals

def parse_raw_csi(csv_path):
    parsed = load_csi(csv_path)
    return parsed.time, parsed.amplitudes, parsed.phases, parsed.records

def mask_null_subcarriers(amplitudes, min_mean_energy=1.0):
    mask = np.mean(amplitudes, axis=0) >= min_mean_energy
    return amplitudes[:, mask], np.where(mask)[0], np.where(~mask)[0]

def hampel_filter(data, window_size=7, n_sigmas=3.0):
    result = data.copy(); radius = window_size // 2
    for column in range(data.shape[1]):
        for index in range(radius, len(data) - radius):
            window = data[index - radius:index + radius + 1, column]
            median = np.median(window); mad = np.median(np.abs(window - median))
            if mad > 1e-6 and abs(data[index, column] - median) > n_sigmas * 1.4826 * mad: result[index, column] = median
    return result

def butterworth_bandpass(data, fs, lowcut=0.2, highcut=10.0, order=4):
    validate_packet_intervals(np.arange(data.shape[0], dtype=float) / fs)
    if fs <= 2 * highcut: raise ValueError(f"sampling rate {fs:.3f} Hz is too low for the {highcut:g} Hz filter")
    b, a = butter(order, [lowcut / (0.5 * fs), highcut / (0.5 * fs)], btype='band')
    return filtfilt(b, a, data, axis=0)

def zscore_normalize(data):
    mean, scale = np.mean(data, axis=0), np.std(data, axis=0)
    scale[scale == 0] = 1.0
    return (data - mean) / scale

def extract_pca(data, n_components=3):
    centered = data - np.mean(data, axis=0)
    _, singular_values, vectors = np.linalg.svd(centered, full_matrices=False)
    components = centered @ vectors[:n_components].T
    variance = singular_values ** 2 / np.sum(singular_values ** 2) * 100.0
    return components, variance[:n_components]

def sanitize_phase(raw_phases):
    sanitized = np.zeros_like(raw_phases); indices = np.arange(raw_phases.shape[1])
    for row, phase in enumerate(raw_phases):
        unwrapped = np.unwrap(phase); slope, intercept = np.polyfit(indices, unwrapped, 1)
        sanitized[row] = unwrapped - (slope * indices + intercept)
    return sanitized

def run_advanced_pipeline(csv_path):
    time, raw, phases, records = parse_raw_csi(csv_path)
    fs = validate_packet_intervals(time)
    active, active_indices, null_indices = mask_null_subcarriers(raw)
    despiked = hampel_filter(active)
    bandpassed = butterworth_bandpass(despiked, fs)
    normalized = zscore_normalize(bandpassed)
    pca, variance = extract_pca(normalized)
    return {'filename': os.path.basename(csv_path), 'time': time, 'fs': fs, 'raw': raw, 'phases': phases, 'records': records, 'active_amps': active, 'active_indices': active_indices, 'null_indices': null_indices, 'despiked': despiked, 'bandpassed': bandpassed, 'normalized': normalized, 'pca': pca, 'var_exp': variance}
