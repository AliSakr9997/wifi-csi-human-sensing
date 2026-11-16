import glob
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from csi_processing import load_csi, validate_packet_intervals

DATA_DIR = r'C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data'
DOCS_DIR = r'C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\docs'

def get_latest_file(pattern):
    files = glob.glob(os.path.join(DATA_DIR, pattern))
    if not files: raise FileNotFoundError(f'No files matching {pattern}')
    return max(files, key=os.path.getmtime)

def parse_and_process(csv_path):
    parsed = load_csi(csv_path)
    fs = validate_packet_intervals(parsed.time)
    active = parsed.amplitudes[:, parsed.amplitudes.mean(axis=0) >= 1.0]
    median = np.median(active, axis=0)
    band = active - median
    b, a = butter(4, [0.2 / (0.5 * fs), 10.0 / (0.5 * fs)], btype='band')
    filtered = filtfilt(b, a, band, axis=0)
    centered = filtered - filtered.mean(axis=0)
    _, singular, vectors = np.linalg.svd(centered, full_matrices=False)
    return {'file': os.path.basename(csv_path), 'time': parsed.time, 'fs': fs, 'raw': parsed.amplitudes, 'filtered': filtered, 'pca1': centered @ vectors[0], 'var_exp': singular[0] ** 2 / np.sum(singular ** 2) * 100.0}

def generate_comparison_plots():
    empty = parse_and_process(get_latest_file('empty_room_*.csv'))
    walking = parse_and_process(get_latest_file('person_walking_*.csv'))
    sub = min(100, empty['raw'].shape[1] - 1)
    fig, axes = plt.subplots(2, 1, figsize=(15, 8), sharex=False)
    axes[0].plot(empty['time'], empty['raw'][:, sub], label='Empty room')
    axes[0].plot(walking['time'], walking['raw'][:, sub], label='Walking')
    axes[0].set_title('Raw CSI amplitude'); axes[0].legend()
    axes[1].plot(empty['time'], empty['pca1'], label='Empty room')
    axes[1].plot(walking['time'], walking['pca1'], label='Walking')
    axes[1].set_title('Validated-rate cleaned PCA motion profile'); axes[1].set_xlabel('Time (seconds)'); axes[1].legend()
    os.makedirs(DOCS_DIR, exist_ok=True)
    fig.savefig(os.path.join(DOCS_DIR, '30s_cleaned_comparison.png'), dpi=160, bbox_inches='tight')
    plt.close(fig)

if __name__ == '__main__': generate_comparison_plots()
