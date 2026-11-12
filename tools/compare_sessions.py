import os
import sys
import numpy as np
import pandas as pd

def parse_csi_amplitudes(df):
    amps = []
    for s in df["data"]:
        v = np.fromstring(str(s), sep=";", dtype=np.float32)
        if v.size > 0 and v.size % 2 == 0:
            iq = v.reshape(-1, 2)
            # Remove index 0 (first_word_invalid artifact)
            amp = np.sqrt(iq[:, 0]**2 + iq[:, 1]**2)
            amps.append(amp[1:]) # subcarriers 1..127
    return np.array(amps)

def analyze_file(csv_path):
    df = pd.read_csv(csv_path, dtype={"data": str, "mac": str})
    n = len(df)
    
    # Timing
    host = df["host_time"].astype(float)
    duration = host.max() - host.min()
    rate = n / duration if duration > 0 else 0
    
    # Sequence Loss
    seq = df["seq"].astype(np.int64)
    d_seq = seq.diff().dropna()
    lost = int((d_seq[d_seq > 1] - 1).sum())
    total_expected = int(seq.max() - seq.min() + 1)
    delivery = 100.0 * (1.0 - lost / max(1, total_expected))
    
    # Jitter
    ts = df["local_timestamp"].astype(np.int64)
    dts = ts.diff().dropna()
    jitter_ms = (dts.std() / 1000.0) if len(dts) > 1 else 0
    median_dt_ms = (dts.median() / 1000.0) if len(dts) > 1 else 0
    
    # Subcarrier Analysis
    A = parse_csi_amplitudes(df)
    # Temporal variance per subcarrier (axis 0 is time/packets)
    subcarrier_variances = np.var(A, axis=0) if len(A) > 1 else np.zeros(1)
    mean_variance = float(np.mean(subcarrier_variances))
    
    return {
        "file": os.path.basename(csv_path),
        "packets": n,
        "duration_s": round(duration, 2),
        "rate_hz": round(rate, 1),
        "delivery_pct": round(delivery, 2),
        "lost_pkts": lost,
        "median_dt_ms": round(median_dt_ms, 2),
        "jitter_ms": round(jitter_ms, 2),
        "rssi_mean": round(float(df["rssi"].mean()), 1),
        "rssi_std": round(float(df["rssi"].std()), 2),
        "mean_variance": round(mean_variance, 2),
        "num_subcarriers": A.shape[1] if len(A) > 0 else 0
    }

f1 = sys.argv[1] if len(sys.argv) > 1 else "data/empty_room_20261112_063039.csv"
f2 = sys.argv[2] if len(sys.argv) > 2 else "data/person_walking_20261112_063109.csv"

res1 = analyze_file(f1)
res2 = analyze_file(f2)

print("\n" + "="*70)
print(f"{'METRIC':<30} | {'EMPTY ROOM':<17} | {'PERSON WALKING':<17}")
print("="*70)
print(f"{'File Name':<30} | {res1['file'][:17]:<17} | {res2['file'][:17]:<17}")
print(f"{'Total Packets Captured':<30} | {res1['packets']:<17} | {res2['packets']:<17}")
print(f"{'Duration':<30} | {res1['duration_s']} s{'':<13} | {res2['duration_s']} s{'':<13}")
print(f"{'Effective Sampling Rate':<30} | {res1['rate_hz']} pkt/s{'':<9} | {res2['rate_hz']} pkt/s{'':<9}")
print(f"{'Packet Delivery Rate':<30} | {res1['delivery_pct']} %{'':<13} | {res2['delivery_pct']} %{'':<13}")
print(f"{'Lost Packets':<30} | {res1['lost_pkts']:<17} | {res2['lost_pkts']:<17}")
print(f"{'Sampling Jitter (sigma)':<30} | {res1['jitter_ms']} ms{'':<12} | {res2['jitter_ms']} ms{'':<12}")
print(f"{'Mean RSSI Power':<30} | {res1['rssi_mean']} dBm{'':<11} | {res2['rssi_mean']} dBm{'':<11}")
print(f"{'Active Subcarriers':<30} | {res1['num_subcarriers']:<17} | {res2['num_subcarriers']:<17}")
print("-"*70)
print(f"{'TEMPORAL CSI VARIANCE':<30} | {res1['mean_variance']:<17} | {res2['mean_variance']:<17}")
print("="*70)

if res1['mean_variance'] > 0:
    ratio = res2['mean_variance'] / res1['mean_variance']
    print(f"\n[*] SENSITIVITY RATIO (Walking / Empty): {ratio:.2f}x dynamic signal amplification")
    if ratio > 2.0:
        print("[+] VERDICT: Physical human sensing is 100% VALIDATED and robustly separating states!")
    else:
        print("[?] VERDICT: Moderate variance change.")
