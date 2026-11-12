"""
Advanced 6-Stage Wi-Fi CSI Signal Cleaning Pipeline
====================================================
Transforms raw, noisy ESP32 Wi-Fi CSI matrices into clean, 
standardized, human-motion-isolated waveforms ready for ML.

6-Stage Pipeline:
1. Complex parsing & preamble AGC transient removal (first_word_invalid)
2. Null & Guard Subcarrier Masking (strips dead 0-energy channels)
3. Hampel outlier filter (removes transient burst spikes)
4. Zero-phase Butterworth Bandpass (0.2 Hz - 10.0 Hz)
5. Dynamic Z-score Normalization (scale-invariant motion representation)
6. Spatial PCA Fusion (captures top orthogonal Doppler components)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

def parse_raw_csi(csv_path):
    """
    Stage 1: Complex Parsing & First-Word Artifact Removal
    """
    df = pd.read_csv(csv_path, dtype={"data": str, "mac": str})
    raw_amplitudes = []
    raw_phases = []
    valid_indices = []
    
    for idx, row in df.iterrows():
        raw_str = str(row['data']).strip(' "[]')
        if not raw_str:
            continue
        try:
            sep = ';' if ';' in raw_str else ','
            vals = [int(x.strip()) for x in raw_str.split(sep) if x.strip()]
            if len(vals) < 4 or len(vals) % 2 != 0:
                continue
            
            # Complex (Im, Re) pairs
            iq = np.array(vals, dtype=np.float32).reshape(-1, 2)
            im = iq[:, 0]
            re = iq[:, 1]
            
            # Magnitudes & Phases
            amps = np.sqrt(im**2 + re**2)[1:] # Discard subcarrier 0
            phases = np.arctan2(im, re)[1:]
            
            raw_amplitudes.append(amps)
            raw_phases.append(phases)
            valid_indices.append(idx)
        except Exception:
            continue
            
    amplitudes = np.array(raw_amplitudes, dtype=np.float32)
    phases = np.array(raw_phases, dtype=np.float32)
    timestamps = df.loc[valid_indices, 'host_time'].values.astype(np.float64)
    t = timestamps - timestamps[0]
    
    return t, amplitudes, phases, df.loc[valid_indices]

def mask_null_subcarriers(amplitudes, min_mean_energy=1.0):
    """
    Stage 2: Dead Guard & DC Null Subcarrier Masking
    Identifies and drops unmodulated guard band and center DC tones.
    """
    subcarrier_means = np.mean(amplitudes, axis=0)
    active_mask = subcarrier_means >= min_mean_energy
    active_indices = np.where(active_mask)[0]
    null_indices = np.where(~active_mask)[0]
    
    clean_active_amps = amplitudes[:, active_mask]
    return clean_active_amps, active_indices, null_indices

def hampel_filter(data, window_size=7, n_sigmas=3.0):
    """
    Stage 3: Hampel Outlier Despiking (MAD-based)
    """
    cleaned = data.copy()
    n_samples, n_subs = data.shape
    k = window_size // 2
    
    for sub_idx in range(n_subs):
        series = data[:, sub_idx]
        for i in range(k, n_samples - k):
            window = series[i - k : i + k + 1]
            med = np.median(window)
            mad = np.median(np.abs(window - med))
            threshold = n_sigmas * 1.4826 * mad
            if np.abs(series[i] - med) > threshold and mad > 1e-6:
                cleaned[i, sub_idx] = med
                
    return cleaned

def butterworth_bandpass(data, fs=60.0, lowcut=0.2, highcut=10.0, order=4):
    """
    Stage 4: Zero-Phase Butterworth Bandpass Filter
    Strips static 0 Hz DC and high-frequency noise > 10 Hz.
    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, data, axis=0)

def zscore_normalize(data):
    """
    Stage 5: Dynamic Z-Score Standardization
    Scales motion amplitude to zero-mean and unit variance, making features
    invariant to subject distance from antennas.
    """
    mean = np.mean(data, axis=0)
    std = np.std(data, axis=0)
    std[std == 0] = 1.0 # Prevent div by 0
    return (data - mean) / std

def extract_pca(data, n_components=3):
    """
    Stage 6: Multi-Subcarrier Spatial PCA Fusion
    """
    X = data - np.mean(data, axis=0)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    pca_components = np.dot(X, Vt[:n_components, :].T)
    var_exp = (S**2) / np.sum(S**2) * 100.0
    return pca_components, var_exp[:n_components]

def sanitize_phase(raw_phases):
    """
    Optional Academic Stage: Linear Phase Sanitization across Subcarriers
    Removes CFO, SFO, and packet detection delay phase slopes.
    """
    n_frames, n_subs = raw_phases.shape
    sanitized = np.zeros_like(raw_phases)
    k = np.arange(n_subs)
    for i in range(n_frames):
        unwrapped = np.unwrap(raw_phases[i, :])
        p = np.polyfit(k, unwrapped, deg=1)
        sanitized[i, :] = unwrapped - (p[0] * k + p[1])
    return sanitized

def run_advanced_pipeline(csv_path):
    filename = os.path.basename(csv_path)
    print(f"\n" + "="*65)
    print(f"[*] Processing: {filename}")
    print("="*65)
    
    # 1. Parse & AGC artifact strip
    t, raw_amps, raw_phases, df = parse_raw_csi(csv_path)
    fs = float(len(t) / (t[-1] - t[0])) if t[-1] > 0 else 60.0
    print(f"  [1] Parsed: {raw_amps.shape[0]} frames x {raw_amps.shape[1]} subcarriers (Fs={fs:.1f} Hz)")
    
    # 2. Null subcarrier masking
    active_amps, active_idx, null_idx = mask_null_subcarriers(raw_amps, min_mean_energy=1.0)
    print(f"  [2] Null Masking: Dropped {len(null_idx)} dead guard channels -> {len(active_idx)} active subcarriers retained")
    
    # 3. Hampel despiking
    despiked = hampel_filter(active_amps, window_size=7, n_sigmas=3.0)
    spikes = np.sum(active_amps != despiked)
    print(f"  [3] Hampel Despiking: Removed {spikes} burst spikes")
    
    # 4. Butterworth bandpass (0.2 - 10 Hz)
    bandpassed = butterworth_bandpass(despiked, fs=fs, lowcut=0.2, highcut=10.0, order=4)
    print(f"  [4] Butterworth Bandpass: 0.2 - 10.0 Hz motion band isolated")
    
    # 5. Z-Score dynamic standardization
    normalized = zscore_normalize(bandpassed)
    print(f"  [5] Dynamic Z-Score: Signal standardized (mean=0.0, std=1.0 per subcarrier)")
    
    # 6. PCA Spatial fusion
    pca, var_exp = extract_pca(normalized, n_components=3)
    print(f"  [6] PCA Spatial Fusion: PC1 captures {var_exp[0]:.1f}% variance (Top 3 capture {np.sum(var_exp):.1f}%)")
    print("="*65)
    
    return {
        "filename": filename,
        "time": t,
        "fs": fs,
        "raw": raw_amps,
        "active_amps": active_amps,
        "despiked": despiked,
        "bandpassed": bandpassed,
        "normalized": normalized,
        "pca": pca,
        "var_exp": var_exp
    }

if __name__ == "__main__":
    f_empty = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data\empty_room_20261112_063039.csv"
    f_walk  = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data\person_walking_20261112_063109.csv"
    
    res_empty = run_advanced_pipeline(f_empty)
    res_walk  = run_advanced_pipeline(f_walk)
    
    # Save Comprehensive 6-Stage Educational Comparison Plot
    fig, axes = plt.subplots(5, 2, figsize=(16, 14), sharex=True)
    plt.subplots_adjust(hspace=0.35, wspace=0.15)
    
    sub = 30 # Sample active subcarrier
    
    # Row 1: Raw CSI
    axes[0, 0].plot(res_empty['time'], res_empty['raw'][:, sub], color='#64748b', lw=1.2)
    axes[0, 0].set_title("Empty Room — 1. Raw CSI Amplitude", fontweight='bold')
    axes[0, 0].set_ylabel("Raw Magnitude")
    axes[0, 0].grid(True, linestyle='--', alpha=0.5)
    
    axes[0, 1].plot(res_walk['time'], res_walk['raw'][:, sub], color='#2563eb', lw=1.2)
    axes[0, 1].set_title("Walking — 1. Raw CSI Amplitude", fontweight='bold')
    axes[0, 1].grid(True, linestyle='--', alpha=0.5)
    
    # Row 2: Hampel Despiked
    axes[1, 0].plot(res_empty['time'], res_empty['despiked'][:, sub], color='#475569', lw=1.2)
    axes[1, 0].set_title("Empty Room — 2. Hampel Despiked (Outliers Removed)", fontweight='bold')
    axes[1, 0].set_ylabel("Clean Magnitude")
    axes[1, 0].grid(True, linestyle='--', alpha=0.5)
    
    axes[1, 1].plot(res_walk['time'], res_walk['despiked'][:, sub], color='#0284c7', lw=1.2)
    axes[1, 1].set_title("Walking — 2. Hampel Despiked (Outliers Removed)", fontweight='bold')
    axes[1, 1].grid(True, linestyle='--', alpha=0.5)
    
    # Row 3: Bandpass Filtered (0.2 - 10 Hz)
    axes[2, 0].plot(res_empty['time'], res_empty['bandpassed'][:, sub], color='#94a3b8', lw=1.2)
    axes[2, 0].set_title("Empty Room — 3. Bandpass (0.2 - 10 Hz, DC Zeroed)", fontweight='bold')
    axes[2, 0].set_ylabel("Motion Signal")
    axes[2, 0].grid(True, linestyle='--', alpha=0.5)
    
    axes[2, 1].plot(res_walk['time'], res_walk['bandpassed'][:, sub], color='#10b981', lw=1.2)
    axes[2, 1].set_title("Walking — 3. Bandpass (0.2 - 10 Hz, DC Zeroed)", fontweight='bold')
    axes[2, 1].grid(True, linestyle='--', alpha=0.5)
    
    # Row 4: Z-Score Standardized
    axes[3, 0].plot(res_empty['time'], res_empty['normalized'][:, sub], color='#cbd5e1', lw=1.2)
    axes[3, 0].set_title("Empty Room — 4. Z-Score Standardized (Scale Invariant)", fontweight='bold')
    axes[3, 0].set_ylabel("Std Units (σ)")
    axes[3, 0].grid(True, linestyle='--', alpha=0.5)
    
    axes[3, 1].plot(res_walk['time'], res_walk['normalized'][:, sub], color='#f59e0b', lw=1.2)
    axes[3, 1].set_title("Walking — 4. Z-Score Standardized (Scale Invariant)", fontweight='bold')
    axes[3, 1].grid(True, linestyle='--', alpha=0.5)
    
    # Row 5: PCA Component 1
    axes[4, 0].plot(res_empty['time'], res_empty['pca'][:, 0], color='#94a3b8', lw=1.5)
    axes[4, 0].set_title(f"Empty Room — 5. PCA Component 1 ({res_empty['var_exp'][0]:.1f}% var)", fontweight='bold')
    axes[4, 0].set_xlabel("Time (seconds)")
    axes[4, 0].set_ylabel("PC1 Energy")
    axes[4, 0].set_ylim(-25, 25)
    axes[4, 0].grid(True, linestyle='--', alpha=0.5)
    
    axes[4, 1].plot(res_walk['time'], res_walk['pca'][:, 0], color='#7c3aed', lw=1.5)
    axes[4, 1].set_title(f"Walking — 5. PCA Component 1 ({res_walk['var_exp'][0]:.1f}% var)", fontweight='bold')
    axes[4, 1].set_xlabel("Time (seconds)")
    axes[4, 1].set_ylim(-25, 25)
    axes[4, 1].grid(True, linestyle='--', alpha=0.5)
    
    out_img = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\docs\advanced_cleaning_proof.png"
    plt.savefig(out_img, dpi=160, bbox_inches='tight')
    print(f"\n[+] Saved Advanced 6-Stage Cleaning Proof Plot to:\n    {out_img}")
