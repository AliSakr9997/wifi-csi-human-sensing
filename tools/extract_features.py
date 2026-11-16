"""Extract the documented 22 amplitude-derived CSI features."""
import glob
import os
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
from scipy.stats import skew, kurtosis, entropy
from csi_processing import load_csi, validate_packet_intervals

DATA_DIR = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data"
OUTPUT_CSV = os.path.join(DATA_DIR, "extracted_features.csv")
WINDOW_SEC = 1.5
STEP_SEC = 0.5

def parse_and_clean_file(csv_path):
    try:
        parsed = load_csi(csv_path)
    except (ValueError, KeyError, OSError):
        return None
    if len(parsed.time) < 60:
        return None
    fs = validate_packet_intervals(parsed.time)
    raw = parsed.amplitudes
    active = raw[:, np.mean(raw, axis=0) >= 1.0]
    rolling = pd.DataFrame(active)
    median = rolling.rolling(7, center=True, min_periods=1).median().to_numpy()
    mad = pd.DataFrame(np.abs(active - median)).rolling(7, center=True, min_periods=1).median().to_numpy()
    despiked = np.where((np.abs(active - median) > 3.0 * 1.4826 * mad) & (mad > 1e-6), median, active)
    nyq = 0.5 * fs
    if not 10.0 < nyq:
        raise ValueError(f"sampling rate {fs:.3f} Hz is too low for the 10 Hz filter")
    b, a = butter(4, [0.2 / nyq, 10.0 / nyq], btype='band')
    bandpassed = filtfilt(b, a, despiked, axis=0)
    X = bandpassed - np.mean(bandpassed, axis=0)
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    return {'time': parsed.time, 'fs': fs, 'rssi': parsed.records['rssi'].to_numpy(dtype=np.float32), 'bandpassed': bandpassed, 'pca1': X @ vt[0], 'pca2': X @ vt[1]}

def extract_window_features(pc1, pc2, bandpassed, rssi, fs):
    features = {}
    median = float(np.median(pc1))
    q75, q25 = np.percentile(pc1, [75, 25])
    features.update({'pc1_var': float(np.var(pc1)), 'pc1_std': float(np.std(pc1)), 'pc1_mad': float(np.median(np.abs(pc1 - median))), 'pc1_iqr': float(q75 - q25), 'pc1_ptp': float(np.ptp(pc1)), 'pc1_skew': float(skew(pc1)), 'pc1_kurt': float(kurtosis(pc1)), 'pc1_rms': float(np.sqrt(np.mean(pc1 ** 2))), 'pc1_zcr': float(np.sum(np.diff(np.sign(pc1)) != 0) / len(pc1))})
    features.update({'pc2_var': float(np.var(pc2)), 'pc2_std': float(np.std(pc2)), 'pc2_mad': float(np.median(np.abs(pc2 - np.median(pc2)))), 'pc2_ptp': float(np.ptp(pc2))})
    psd = np.abs(np.fft.rfft(pc1)) ** 2
    freqs = np.fft.rfftfreq(len(pc1), d=1.0 / fs)
    total = float(np.sum(psd) + 1e-9)
    dominant = np.argmax(psd[1:]) + 1 if len(psd) > 1 else 0
    features.update({'dominant_freq': float(freqs[dominant]), 'energy_low': float(np.sum(psd[(freqs >= .2) & (freqs < 1.5)]) / total), 'energy_mid': float(np.sum(psd[(freqs >= 1.5) & (freqs < 4.0)]) / total), 'energy_high': float(np.sum(psd[(freqs >= 4.0) & (freqs <= 10.0)]) / total), 'spectral_entropy': float(entropy(psd / total + 1e-12))})
    variances = np.var(bandpassed, axis=0)
    features.update({'sub_var_mean': float(np.mean(variances)), 'sub_var_std': float(np.std(variances)), 'rssi_mean': float(np.mean(rssi)), 'rssi_std': float(np.std(rssi))})
    return features

def determine_label(filename):
    name = filename.lower()
    if 'empty' in name or 'baseline' in name: return 'empty_room'
    if 'walk' in name: return 'walking'
    if 'sit' in name: return 'sitting'
    if 'wave' in name: return 'hand_wave'
    return None

def build_feature_dataset(data_dir=DATA_DIR, window_sec=WINDOW_SEC, step_sec=STEP_SEC):
    rows = []
    for path in glob.glob(os.path.join(data_dir, '*.csv')):
        name, label = os.path.basename(path), determine_label(os.path.basename(path))
        if not label or 'extracted_features' in name: continue
        result = parse_and_clean_file(path)
        if result is None: continue
        t, fs = result['time'], result['fs']
        window, step = int(window_sec * fs), int(step_sec * fs)
        for start in range(0, len(t) - window + 1, step):
            end = start + window
            row = extract_window_features(result['pca1'][start:end], result['pca2'][start:end], result['bandpassed'][start:end], result['rssi'][start:end], fs)
            row.update({'label': label, 'source_file': name, 'win_start_t': round(float(t[start]), 2), 'win_end_t': round(float(t[end - 1]), 2)})
            rows.append(row)
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_CSV, index=False)
    return result

if __name__ == '__main__':
    build_feature_dataset()
