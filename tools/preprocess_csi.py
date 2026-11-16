"""CSI preprocessing using canonical parsing and validated packet timing."""
import argparse
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from csi_processing import load_csi, validate_packet_intervals

def load_csi_data(csv_path):
    parsed = load_csi(csv_path)
    return parsed.time, parsed.amplitudes, parsed.records

def butter_bandpass_filter(data, lowcut=0.2, highcut=10.0, fs=60.0, order=4):
    if fs <= 2 * highcut:
        raise ValueError(f"sampling rate {fs:.3f} Hz is too low for the {highcut:g} Hz filter")
    b, a = butter(order, [lowcut / (0.5 * fs), highcut / (0.5 * fs)], btype='band')
    return filtfilt(b, a, data, axis=0)

def select_sensitive_subcarriers(amplitudes, top_k=10):
    return np.argsort(np.var(amplitudes, axis=0))[::-1][:top_k]

def plot_preprocessing_results(t, raw_amps, filtered_amps, top_sub, save_path=None):
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].plot(t, raw_amps[:, top_sub]); axes[0].set_title('Raw CSI amplitude')
    axes[1].plot(t, filtered_amps[:, top_sub]); axes[1].set_title('Butterworth bandpass (0.2-10 Hz)')
    for index in select_sensitive_subcarriers(filtered_amps, 5): axes[2].plot(t, filtered_amps[:, index], alpha=.7)
    axes[2].set_title('Top sensitive subcarriers'); axes[2].set_xlabel('Time (seconds)')
    plt.tight_layout()
    if save_path: plt.savefig(save_path, dpi=200)
    else: plt.show()

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('file', nargs='?', default='data/person_walking_20261024_035105.csv'); parser.add_argument('--save-plot', default='docs/preprocessed_walking_example.png'); args = parser.parse_args()
    if not os.path.exists(args.file): print(f"[!] Error: File '{args.file}' not found."); return 1
    t, raw, _ = load_csi_data(args.file)
    fs = validate_packet_intervals(t)
    filtered = butter_bandpass_filter(raw, fs=fs)
    os.makedirs(os.path.dirname(args.save_plot) or '.', exist_ok=True)
    plot_preprocessing_results(t, raw, filtered, int(select_sensitive_subcarriers(filtered, 1)[0]), args.save_plot)
    print(f'[SUCCESS] preprocessing completed with validated Fs={fs:.3f} Hz')
    return 0

if __name__ == '__main__': sys.exit(main())
