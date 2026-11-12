import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

def load_and_filter(csv_path):
    df = pd.read_csv(csv_path, dtype={"data": str, "mac": str})
    amps = []
    for s in df["data"]:
        raw_str = str(s).strip(' "[]')
        if not raw_str:
            continue
        sep = ';' if ';' in raw_str else ','
        vals = [int(x.strip()) for x in raw_str.split(sep) if x.strip()]
        a = [np.sqrt(vals[i]**2 + vals[i+1]**2) for i in range(0, len(vals)-1, 2)]
        if a:
            amps.append(a[1:]) # subcarriers 1..127
    
    A = np.array(amps)
    t = np.linspace(0, 15, len(A))
    
    # Butterworth Bandpass Filter (0.2 - 10 Hz at 60 Hz sampling)
    b, a = butter(4, [0.2 / 30.0, 10.0 / 30.0], btype='band')
    filtered = filtfilt(b, a, A, axis=0)
    
    return t, A, filtered

f_empty = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data\empty_room_20261112_063039.csv"
f_walk  = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data\person_walking_20261112_063109.csv"

t_empty, A_empty, F_empty = load_and_filter(f_empty)
t_walk,  A_walk,  F_walk  = load_and_filter(f_walk)

# Pick the subcarrier with highest walking variance
var_walk = np.var(A_walk, axis=0)
top_sub = int(np.argmax(var_walk))

fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=False)
plt.subplots_adjust(hspace=0.35)

# 1. Raw Amplitudes
axes[0].plot(t_empty, A_empty[:, top_sub], color='#94a3b8', alpha=0.8, label=f'Empty Room (Subcarrier #{top_sub})')
axes[0].plot(t_walk,  A_walk[:, top_sub],  color='#3b82f6', alpha=0.9, label=f'Person Walking (Subcarrier #{top_sub})')
axes[0].set_title(f"1. Raw CSI Amplitude — Subcarrier #{top_sub}", fontsize=12, fontweight='bold')
axes[0].set_ylabel("Raw Amplitude")
axes[0].grid(True, linestyle='--', alpha=0.5)
axes[0].legend(loc='upper right')

# 2. Bandpass Filtered (Human Motion Waveform)
axes[1].plot(t_empty, F_empty[:, top_sub], color='#94a3b8', alpha=0.8, label='Empty Room (Static)')
axes[1].plot(t_walk,  F_walk[:, top_sub],  color='#10b981', alpha=0.9, label='Person Walking (Doppler Waves)')
axes[1].set_title("2. Bandpass Filtered (0.2 - 10 Hz) — Pure Human Motion Signature", fontsize=12, fontweight='bold')
axes[1].set_ylabel("Motion Energy")
axes[1].grid(True, linestyle='--', alpha=0.5)
axes[1].legend(loc='upper right')

# 3. Variance across all 127 Subcarriers
sub_idx = np.arange(1, A_empty.shape[1] + 1)
axes[2].bar(sub_idx - 0.2, np.var(A_empty, axis=0), width=0.4, color='#94a3b8', label='Empty Room Variance')
axes[2].bar(sub_idx + 0.2, np.var(A_walk, axis=0),  width=0.4, color='#f59e0b', label='Walking Variance')
axes[2].set_title("3. Temporal Variance Across All 127 Subcarriers", fontsize=12, fontweight='bold')
axes[2].set_xlabel("Subcarrier Index (1 to 127)")
axes[2].set_ylabel("Variance (σ²)")
axes[2].grid(True, linestyle='--', alpha=0.5)
axes[2].legend(loc='upper right')

out_png = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\docs\live_validation_test.png"
plt.savefig(out_png, dpi=150, bbox_inches='tight')
print(f"[+] Comparison plot successfully saved to: {out_png}")
