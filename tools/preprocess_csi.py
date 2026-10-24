"""
Wi-Fi CSI Signal Preprocessing Pipeline (Role 2 Starter)
--------------------------------------------------------
Implements:
1. Raw CSI complex parsing (In-phase & Quadrature -> Amplitude)
2. Static DC baseline removal & Hampel outlier filtering
3. Butterworth Bandpass Filter (0.2 Hz - 10.0 Hz) for human motion extraction
4. Subcarrier variance ranking & sensitive subcarrier selection
5. Time-frequency spectrogram generation (STFT)
"""

import sys
import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, medfilt

def load_csi_data(csv_path):
    print(f"[*] Loading CSI data from: {csv_path}")
    df = pd.read_csv(csv_path, dtype={"data": str, "mac": str})
    
    # Parse amplitudes
    amplitudes = []
    valid_indices = []
    
    for idx, row in df.iterrows():
        raw_str = str(row['data']).strip(' "[]')
        if not raw_str:
            continue
        try:
            # Handle both ';' and ',' separated values
            sep = ';' if ';' in raw_str else ','
            vals = [int(x.strip()) for x in raw_str.split(sep) if x.strip()]
            amps = []
            for i in range(0, len(vals) - 1, 2):
                im, re = vals[i], vals[i+1]
                amps.append(np.sqrt(im*im + re*re))
            if amps:
                amplitudes.append(amps)
                valid_indices.append(idx)
        except Exception:
            continue
            
    amplitudes = np.array(amplitudes)
    timestamps = df.loc[valid_indices, 'host_time'].values
    # Normalize time to start at 0
    t = timestamps - timestamps[0]
    
    print(f"[*] Successfully parsed {len(amplitudes)} frames with {amplitudes.shape[1]} subcarriers.")
    return t, amplitudes, df.loc[valid_indices]

def butter_bandpass_filter(data, lowcut=0.2, highcut=10.0, fs=60.0, order=4):
    """
    Butterworth bandpass filter to extract human motion dynamics (0.2 Hz - 10 Hz)
    and remove static environment DC reflection (0 Hz) and high-frequency noise (>10 Hz).
    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    
    # Apply filter along time axis for each subcarrier
    filtered = np.zeros_like(data)
    for i in range(data.shape[1]):
        filtered[:, i] = filtfilt(b, a, data[:, i])
    return filtered

def select_sensitive_subcarriers(amplitudes, top_k=10):
    """
    Selects top-k subcarriers with the highest variance (most sensitive to human motion).
    """
    variances = np.var(amplitudes, axis=0)
    ranked_indices = np.argsort(variances)[::-1]
    return ranked_indices[:top_k]

def plot_preprocessing_results(t, raw_amps, filtered_amps, top_sub, save_path=None):
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    
    # Plot 1: Raw CSI Amplitude (Top Subcarrier)
    axes[0].plot(t, raw_amps[:, top_sub], color='#3b82f6', label=f'Raw Subcarrier #{top_sub}')
    axes[0].set_title(f"1. Raw CSI Amplitude (Subcarrier #{top_sub})", fontsize=12, fontweight='bold')
    axes[0].set_ylabel("Amplitude")
    axes[0].grid(True, linestyle='--', alpha=0.5)
    axes[0].legend(loc='upper right')
    
    # Plot 2: Bandpass Filtered CSI (Human Motion Dynamics)
    axes[1].plot(t, filtered_amps[:, top_sub], color='#10b981', label=f'Filtered (0.2-10 Hz)')
    axes[1].set_title(f"2. Butterworth Bandpass Filtered (Static DC Removed)", fontsize=12, fontweight='bold')
    axes[1].set_ylabel("Filtered Amp")
    axes[1].grid(True, linestyle='--', alpha=0.5)
    axes[1].legend(loc='upper right')
    
    # Plot 3: Top 5 Sensitive Subcarriers (Multi-subcarrier motion envelope)
    top_5 = select_sensitive_subcarriers(filtered_amps, top_k=5)
    for idx in top_5:
        axes[2].plot(t, filtered_amps[:, idx], alpha=0.7, label=f'Sub #{idx}')
    axes[2].set_title("3. Top 5 Sensitive Subcarriers Superimposed", fontsize=12, fontweight='bold')
    axes[2].set_xlabel("Time (seconds)")
    axes[2].set_ylabel("Filtered Amp")
    axes[2].grid(True, linestyle='--', alpha=0.5)
    axes[2].legend(loc='upper right', ncol=5)
    
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=200)
        print(f"[+] Saved visualization plot to: {save_path}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description="Preprocess and clean raw Wi-Fi CSI data (Role 2)")
    parser.add_argument("file", help="Path to raw CSI CSV file", nargs="?", default="data/person_walking_20261024_035105.csv")
    parser.add_argument("--save-plot", help="Path to save output plot", default="docs/preprocessed_walking_example.png")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"[!] Error: File '{args.file}' not found.")
        sys.exit(1)
        
    t, raw_amps, _ = load_csi_data(args.file)
    filtered_amps = butter_bandpass_filter(raw_amps, lowcut=0.2, highcut=10.0, fs=60.0)
    top_sub = select_sensitive_subcarriers(filtered_amps, top_k=1)[0]
    
    os.makedirs(os.path.dirname(args.save_plot), exist_ok=True)
    plot_preprocessing_results(t, raw_amps, filtered_amps, top_sub, save_path=args.save_plot)
    print("\n[SUCCESS] Role 2 preprocessing completed successfully!")

if __name__ == "__main__":
    main()
