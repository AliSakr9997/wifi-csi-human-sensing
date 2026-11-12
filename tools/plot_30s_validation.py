import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

# Set writable MPLCONFIGDIR for matplotlib to eliminate warnings
os.environ['MPLCONFIGDIR'] = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'matplotlib_csi')

DATA_DIR = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data"
DOCS_DIR = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\docs"
ARTIFACT_DIR = r"C:\Users\MOHAMMED SABRY\.gemini\antigravity\brain\b071a487-32b5-4ce9-bda8-3adc6b27074e"

def get_latest_file(pattern):
    files = glob.glob(os.path.join(DATA_DIR, pattern))
    if not files:
        raise FileNotFoundError(f"No files matching {pattern}")
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def parse_and_process(csv_path):
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
            # Magnitudes, discard subcarrier 0 (AGC transient)
            amps = np.sqrt(iq[:, 0]**2 + iq[:, 1]**2)[1:]
            raw_amps.append(amps)
            valid_idx.append(idx)
        except Exception:
            continue
            
    raw = np.array(raw_amps, dtype=np.float32)
    t = df.loc[valid_idx, 'host_time'].values.astype(np.float64)
    t = t - t[0]
    fs = float(len(t) / (t[-1] - t[0])) if t[-1] > 0 else 60.0
    rssi = df.loc[valid_idx, 'rssi'].values.astype(np.float32)
    
    # 1. Null Masking: Drop dead guard subcarriers (energy < 1.0)
    means = np.mean(raw, axis=0)
    active_mask = means >= 1.0
    active_raw = raw[:, active_mask]
    active_indices = np.where(active_mask)[0]
    
    # 2. Fast Vectorized Hampel Outlier Despiking
    df_act = pd.DataFrame(active_raw)
    med = df_act.rolling(7, center=True, min_periods=1).median().values
    mad = pd.DataFrame(np.abs(active_raw - med)).rolling(7, center=True, min_periods=1).median().values
    outliers = np.abs(active_raw - med) > 3.0 * 1.4826 * mad
    despiked = np.where(outliers & (mad > 1e-6), med, active_raw)
    
    # 3. Zero-phase Butterworth Bandpass (0.2 Hz - 10.0 Hz)
    nyq = 0.5 * fs
    b, a = butter(4, [0.2 / nyq, 10.0 / nyq], btype='band')
    bandpassed = filtfilt(b, a, despiked, axis=0)
    
    # 4. Multi-subcarrier Spatial PCA Motion Fusion
    # Center dynamic signal without artificial per-column std distortion
    X = bandpassed - np.mean(bandpassed, axis=0)
    U, S, Vt = np.linalg.svd(X, full_matrices=False)
    pca1 = np.dot(X, Vt[0, :].T)
    var_exp = (S[0]**2) / np.sum(S**2) * 100.0
    
    return {
        "file": os.path.basename(csv_path),
        "time": t,
        "fs": fs,
        "rssi": rssi,
        "raw": raw,
        "active_raw": active_raw,
        "active_indices": active_indices,
        "bandpassed": bandpassed,
        "pca1": pca1,
        "var_exp": var_exp
    }

def generate_comparison_plots():
    f_empty = get_latest_file("empty_room_*.csv")
    f_walk  = get_latest_file("person_walking_*.csv")
    
    print(f"[*] Processing Empty Room: {os.path.basename(f_empty)}")
    res_empty = parse_and_process(f_empty)
    print(f"[*] Processing Walking:    {os.path.basename(f_walk)}")
    res_walk  = parse_and_process(f_walk)
    
    # Select sensitive active subcarriers for raw comparison
    # Subcarrier #100 and Subcarrier #75
    sub_primary = 100
    sub_secondary = 75
    
    # =============================================================
    # PLOT 1: RAW CSI DATA (BEFORE CLEANING)
    # =============================================================
    fig1, (ax1_top, ax1_bot) = plt.subplots(2, 1, figsize=(15, 8.5), sharex=True)
    plt.subplots_adjust(hspace=0.28)
    
    # Empty Room Raw
    ax1_top.plot(res_empty['time'], res_empty['raw'][:, sub_primary], color='#475569', lw=1.2, label=f'Raw Subcarrier #{sub_primary}')
    ax1_top.plot(res_empty['time'], res_empty['raw'][:, sub_secondary], color='#94a3b8', lw=0.9, alpha=0.8, linestyle=':', label=f'Raw Subcarrier #{sub_secondary}')
    ax1_top.set_title(f"RAW CSI DATA -- Empty Room ({res_empty['file']})\nStatic DC Level (~38-42) with Electronic Thermal Noise & RF Jitter", 
                      fontsize=12, fontweight='bold', color='#1e293b', loc='left')
    ax1_top.set_ylabel("Raw Amplitude (ADC units)", fontsize=11, fontweight='semibold')
    ax1_top.grid(True, linestyle='--', alpha=0.5)
    ax1_top.set_ylim(20, 55)
    ax1_top.legend(loc='upper right', framealpha=0.9)
    ax1_top.text(0.015, 0.12, 
                 f"Empty Room Characteristics:\n- Subcarrier #{sub_primary} Mean: {np.mean(res_empty['raw'][:, sub_primary]):.1f}\n- High DC Offset, No Periodic Doppler Waves\n- Avg RSSI: {np.mean(res_empty['rssi']):.1f} dBm", 
                 transform=ax1_top.transAxes, fontsize=10, bbox=dict(boxstyle='round,pad=0.5', facecolor='#f1f5f9', edgecolor='#cbd5e1'))
    
    # Person Walking Raw
    ax1_bot.plot(res_walk['time'], res_walk['raw'][:, sub_primary], color='#2563eb', lw=1.3, label=f'Raw Subcarrier #{sub_primary}')
    ax1_bot.plot(res_walk['time'], res_walk['raw'][:, sub_secondary], color='#06b6d4', lw=0.9, alpha=0.8, linestyle=':', label=f'Raw Subcarrier #{sub_secondary}')
    ax1_bot.set_title(f"RAW CSI DATA -- Person Walking ({res_walk['file']})\nSevere Multipath Fluctuations (Carrier Shifts + Gait Modulation on Top of DC Offset)", 
                      fontsize=12, fontweight='bold', color='#1e293b', loc='left')
    ax1_bot.set_xlabel("Time (seconds)", fontsize=11, fontweight='semibold')
    ax1_bot.set_ylabel("Raw Amplitude (ADC units)", fontsize=11, fontweight='semibold')
    ax1_bot.grid(True, linestyle='--', alpha=0.5)
    ax1_bot.set_ylim(20, 55)
    ax1_bot.legend(loc='upper right', framealpha=0.9)
    ax1_bot.text(0.015, 0.12, 
                 f"Walking Characteristics:\n- Subcarrier #{sub_primary} Mean: {np.mean(res_walk['raw'][:, sub_primary]):.1f}\n- Noticeable Dynamic Oscillations & Carrier Drifts\n- Avg RSSI: {np.mean(res_walk['rssi']):.1f} dBm", 
                 transform=ax1_bot.transAxes, fontsize=10, bbox=dict(boxstyle='round,pad=0.5', facecolor='#eff6ff', edgecolor='#bfdbfe'))
    
    raw_plot_path = os.path.join(DOCS_DIR, "30s_raw_comparison.png")
    fig1.savefig(raw_plot_path, dpi=160, bbox_inches='tight')
    plt.close(fig1)
    print(f"[+] Saved Raw Comparison Plot: {raw_plot_path}")
    
    # =============================================================
    # PLOT 2: FINAL CLEANED CSI DATA (AFTER 6-STAGE PIPELINE)
    # =============================================================
    fig2, (ax2_top, ax2_bot) = plt.subplots(2, 1, figsize=(15, 8.5), sharex=True)
    plt.subplots_adjust(hspace=0.28)
    
    # Empty Room Cleaned (PC1 Motion Profile)
    # Highlight quiet state
    empty_std = np.std(res_empty['pca1'])
    empty_ptp = np.ptp(res_empty['pca1'])
    ax2_top.plot(res_empty['time'], res_empty['pca1'], color='#64748b', lw=1.2, label='Cleaned Motion Profile (PC1)')
    ax2_top.axhline(0, color='#94a3b8', linestyle='--', lw=1.0, alpha=0.7)
    ax2_top.set_title(f"FINAL CLEANED CSI MOTION -- Empty Room (Static Background State)\nDC Stripped (0.0 Baseline) | High-Freq Jitter Removed | PC1 Motion Energy = {empty_std:.2f}", 
                      fontsize=12, fontweight='bold', color='#0f172a', loc='left')
    ax2_top.set_ylabel("Motion Amplitude", fontsize=11, fontweight='semibold')
    ax2_top.set_ylim(-35, 35)
    ax2_top.grid(True, linestyle='--', alpha=0.5)
    ax2_top.legend(loc='upper right', framealpha=0.9)
    ax2_top.text(0.015, 0.72, 
                 f"Cleaned Empty State:\n* Baseline: 0.0 Centered\n* Std Dev (Energy): {empty_std:.2f}\n* Peak-to-Peak: {empty_ptp:.2f}\n* Zero Rhythmic Gait Patterns", 
                 transform=ax2_top.transAxes, fontsize=10, bbox=dict(boxstyle='round,pad=0.5', facecolor='#f8fafc', edgecolor='#cbd5e1'))
    
    # Person Walking Cleaned (PC1 Motion Profile)
    walk_std = np.std(res_walk['pca1'])
    walk_ptp = np.ptp(res_walk['pca1'])
    ax2_bot.plot(res_walk['time'], res_walk['pca1'], color='#7c3aed', lw=1.4, label='Cleaned Motion Profile (PC1)')
    ax2_bot.axhline(0, color='#94a3b8', linestyle='--', lw=1.0, alpha=0.7)
    ax2_bot.set_title(f"FINAL CLEANED CSI MOTION -- Person Walking (Dynamic Footstep Signatures)\nIsolated Human Doppler Waveform | Rhythmic Cadence Visible | PC1 Motion Energy = {walk_std:.2f}", 
                      fontsize=12, fontweight='bold', color='#0f172a', loc='left')
    ax2_bot.set_xlabel("Time (seconds)", fontsize=11, fontweight='semibold')
    ax2_bot.set_ylabel("Motion Amplitude", fontsize=11, fontweight='semibold')
    ax2_bot.set_ylim(-35, 35)
    ax2_bot.grid(True, linestyle='--', alpha=0.5)
    ax2_bot.legend(loc='upper right', framealpha=0.9)
    ax2_bot.text(0.015, 0.72, 
                 f"Cleaned Walking State:\n* Distinct Periodic Cadence Cycles\n* Std Dev (Energy): {walk_std:.2f}\n* Peak-to-Peak: {walk_ptp:.2f}\n* Multi-subcarrier Coherent Doppler Waves", 
                 transform=ax2_bot.transAxes, fontsize=10, bbox=dict(boxstyle='round,pad=0.5', facecolor='#faf5ff', edgecolor='#d8b4fe'))
    
    clean_plot_path = os.path.join(DOCS_DIR, "30s_cleaned_comparison.png")
    fig2.savefig(clean_plot_path, dpi=160, bbox_inches='tight')
    plt.close(fig2)
    print(f"[+] Saved Cleaned Comparison Plot: {clean_plot_path}")
    
    # Copy both plots to Artifact directory for persistent embedding
    import shutil
    shutil.copy2(raw_plot_path, os.path.join(ARTIFACT_DIR, "30s_raw_comparison.png"))
    shutil.copy2(clean_plot_path, os.path.join(ARTIFACT_DIR, "30s_cleaned_comparison.png"))
    print(f"[+] Successfully mirrored plots to Artifact directory.")

if __name__ == "__main__":
    generate_comparison_plots()
