"""
Wi-Fi CSI Human Sensing Feature Extractor
==========================================
Role 2 / Role 3 Bridge:
Transforms cleaned continuous Wi-Fi CSI waveforms into ML-ready 
feature vectors using sliding time windows.

Extracts:
1. Time-Domain statistical moments (Variance, MAD, IQR, Skewness, Kurtosis, ZCR, RMS)
2. Frequency-Domain Doppler signatures (Dominant frequency, low/mid/high sub-band energy, Spectral Entropy)
3. Spatial multi-subcarrier metrics (Mean/std subcarrier variance, cross-channel dispersion)
4. Receiver signal power dynamics (Mean RSSI, RSSI standard deviation)
"""

import os
import glob
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
from scipy.stats import skew, kurtosis, entropy

# Configure matplotlib temp dir to prevent warnings
os.environ['MPLCONFIGDIR'] = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'matplotlib_csi')

DATA_DIR = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data"
OUTPUT_CSV = os.path.join(DATA_DIR, "extracted_features.csv")

def parse_and_clean_file(csv_path):
    """
    Parses raw ESP32 CSI CSV and applies the 6-stage cleaning pipeline:
    1. Complex IQ decode & subcarrier 0 drop
    2. Null & guard band subcarrier masking
    3. Fast Hampel outlier filter
    4. Zero-phase Butterworth bandpass (0.2 - 10.0 Hz)
    5. Multi-subcarrier spatial PCA fusion
    """
    df = pd.read_csv(csv_path, dtype={"data": str, "mac": str})
    raw_amps = []
    valid_idx = []
    
    for idx, row in df.iterrows():
        raw_str = str(row['data']).strip(' "[]')
        if not raw_str:
            continue
        try:
            sep = ';' if ';' in raw_str else ','
            vals = [int(x.strip()) for x in raw_str.split(sep) if x.strip()]
            if len(vals) < 4 or len(vals) % 2 != 0:
                continue
            iq = np.array(vals, dtype=np.float32).reshape(-1, 2)
            # Magnitude, drop subcarrier 0
            amps = np.sqrt(iq[:, 0]**2 + iq[:, 1]**2)[1:]
            raw_amps.append(amps)
            valid_idx.append(idx)
        except Exception:
            continue
            
    if len(raw_amps) < 60:
        return None # File too short or corrupted
        
    raw = np.array(raw_amps, dtype=np.float32)
    t = df.loc[valid_idx, 'host_time'].values.astype(np.float64)
    t = t - t[0]
    total_time = t[-1] - t[0]
    fs = float(len(t) / total_time) if total_time > 0 else 60.0
    rssi = df.loc[valid_idx, 'rssi'].values.astype(np.float32)
    
    # 1. Null subcarrier masking (mean energy < 1.0)
    means = np.mean(raw, axis=0)
    active_mask = means >= 1.0
    active_raw = raw[:, active_mask]
    
    # 2. Fast Vectorized Hampel Filter (window=7)
    df_act = pd.DataFrame(active_raw)
    med = df_act.rolling(7, center=True, min_periods=1).median().values
    mad = pd.DataFrame(np.abs(active_raw - med)).rolling(7, center=True, min_periods=1).median().values
    outliers = np.abs(active_raw - med) > 3.0 * 1.4826 * mad
    despiked = np.where(outliers & (mad > 1e-6), med, active_raw)
    
    # 3. Butterworth Bandpass (0.2 Hz - 10.0 Hz)
    nyq = 0.5 * fs
    b, a = butter(4, [0.2 / nyq, 10.0 / nyq], btype='band')
    bandpassed = filtfilt(b, a, despiked, axis=0)
    
    # 4. Multi-subcarrier Spatial PCA (Top 2 components)
    X = bandpassed - np.mean(bandpassed, axis=0)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    pca1 = np.dot(X, Vt[0, :].T)
    pca2 = np.dot(X, Vt[1, :].T)
    
    return {
        "time": t,
        "fs": fs,
        "rssi": rssi,
        "bandpassed": bandpassed,
        "pca1": pca1,
        "pca2": pca2
    }

def extract_window_features(w_pca1, w_pca2, w_bp, w_rssi, fs):
    """
    Extracts 18 distinct features from a single time window.
    """
    feats = {}
    
    # 1. Time-Domain Moments on PC1 (Dominant Motion Profile)
    var1 = float(np.var(w_pca1))
    std1 = float(np.std(w_pca1))
    med1 = float(np.median(w_pca1))
    mad1 = float(np.median(np.abs(w_pca1 - med1)))
    q75, q25 = np.percentile(w_pca1, [75, 25])
    iqr1 = float(q75 - q25)
    ptp1 = float(np.ptp(w_pca1))
    skew1 = float(skew(w_pca1))
    kurt1 = float(kurtosis(w_pca1))
    rms1 = float(np.sqrt(np.mean(w_pca1**2)))
    
    # Zero Crossing Rate (sign changes around mean 0)
    zcr1 = float(np.sum(np.diff(np.sign(w_pca1)) != 0) / len(w_pca1))
    
    feats["pc1_var"] = var1
    feats["pc1_std"] = std1
    feats["pc1_mad"] = mad1
    feats["pc1_iqr"] = iqr1
    feats["pc1_ptp"] = ptp1
    feats["pc1_skew"] = skew1
    feats["pc1_kurt"] = kurt1
    feats["pc1_rms"] = rms1
    feats["pc1_zcr"] = zcr1
    
    # 2. Time-Domain Moments on PC2 (Orthogonal Motion Dynamics)
    feats["pc2_var"] = float(np.var(w_pca2))
    feats["pc2_std"] = float(np.std(w_pca2))
    feats["pc2_mad"] = float(np.median(np.abs(w_pca2 - np.median(w_pca2))))
    feats["pc2_ptp"] = float(np.ptp(w_pca2))
    
    # 3. Frequency-Domain Doppler Signatures (FFT of PC1)
    n = len(w_pca1)
    fft_vals = np.abs(np.fft.rfft(w_pca1))
    freqs = np.fft.rfftfreq(n, d=1.0/fs)
    psd = fft_vals**2
    total_psd = np.sum(psd) + 1e-9
    
    # Dominant peak frequency
    dom_idx = np.argmax(psd[1:]) + 1 if len(psd) > 1 else 0
    feats["dominant_freq"] = float(freqs[dom_idx])
    
    # Doppler sub-band energy
    low_band = (freqs >= 0.2) & (freqs < 1.5)
    mid_band = (freqs >= 1.5) & (freqs < 4.0)
    high_band = (freqs >= 4.0) & (freqs <= 10.0)
    
    feats["energy_low"] = float(np.sum(psd[low_band]) / total_psd)
    feats["energy_mid"] = float(np.sum(psd[mid_band]) / total_psd)
    feats["energy_high"] = float(np.sum(psd[high_band]) / total_psd)
    
    # Spectral Entropy (Degree of spectral concentration vs noise)
    norm_psd = psd / total_psd
    feats["spectral_entropy"] = float(entropy(norm_psd + 1e-12))
    
    # 4. Multi-Subcarrier Spatial Dispersion
    sub_vars = np.var(w_bp, axis=0)
    feats["sub_var_mean"] = float(np.mean(sub_vars))
    feats["sub_var_std"] = float(np.std(sub_vars))
    
    # 5. RSSI Power Dynamics
    feats["rssi_mean"] = float(np.mean(w_rssi))
    feats["rssi_std"] = float(np.std(w_rssi))
    
    return feats

def determine_label(filename):
    """
    Infers activity ground-truth class from filename.
    """
    fname = filename.lower()
    if "empty" in fname or "baseline" in fname:
        return "empty_room"
    elif "walk" in fname:
        return "walking"
    elif "sit" in fname:
        return "sitting"
    elif "wave" in fname:
        return "hand_wave"
    return None

def build_feature_dataset(data_dir=DATA_DIR, window_sec=1.5, step_sec=0.5):
    """
    Batch extracts sliding-window feature vectors from all valid CSI recordings.
    """
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    # Exclude previously generated feature files
    csv_files = [f for f in csv_files if "extracted_features" not in os.path.basename(f)]
    
    all_rows = []
    processed_count = 0
    skipped_count = 0
    
    print(f"[*] Scanning {len(csv_files)} CSV files in {data_dir}...")
    print(f"[*] Window Size: {window_sec}s | Step: {step_sec}s")
    
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        label = determine_label(fname)
        if not label:
            skipped_count += 1
            continue
            
        print(f" -> Processing [{label:10s}]: {fname}...", end="", flush=True)
        res = parse_and_clean_file(fpath)
        if res is None:
            print(" [SKIPPED - too short / corrupt]")
            skipped_count += 1
            continue
            
        t = res["time"]
        fs = res["fs"]
        pca1 = res["pca1"]
        pca2 = res["pca2"]
        bp = res["bandpassed"]
        rssi = res["rssi"]
        
        n_pts = len(t)
        pts_per_win = int(window_sec * fs)
        pts_per_step = int(step_sec * fs)
        
        if pts_per_win <= 0 or pts_per_step <= 0 or n_pts < pts_per_win:
            print(" [SKIPPED - insufficient packets]")
            skipped_count += 1
            continue
            
        win_count = 0
        for start_idx in range(0, n_pts - pts_per_win + 1, pts_per_step):
            end_idx = start_idx + pts_per_win
            
            w_pca1 = pca1[start_idx:end_idx]
            w_pca2 = pca2[start_idx:end_idx]
            w_bp   = bp[start_idx:end_idx, :]
            w_rssi = rssi[start_idx:end_idx]
            
            feats = extract_window_features(w_pca1, w_pca2, w_bp, w_rssi, fs)
            feats["label"] = label
            feats["source_file"] = fname
            feats["win_start_t"] = round(float(t[start_idx]), 2)
            feats["win_end_t"] = round(float(t[end_idx - 1]), 2)
            
            all_rows.append(feats)
            win_count += 1
            
        print(f" [OK: {win_count} windows]")
        processed_count += 1
        
    df_features = pd.DataFrame(all_rows)
    df_features.to_csv(OUTPUT_CSV, index=False)
    
    print("\n" + "="*60)
    print(f"[SUCCESS] Feature Extraction Complete!")
    print(f"[+] Output CSV: {OUTPUT_CSV}")
    print(f"[+] Total Extracted Windows: {len(df_features)}")
    print(f"[+] Total Features per Window: {len(df_features.columns) - 4}")
    print("\n[+] Class Breakdown:")
    print(df_features["label"].value_counts().to_string())
    print("="*60)
    
    return df_features

if __name__ == "__main__":
    build_feature_dataset()
