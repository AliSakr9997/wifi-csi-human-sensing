import os
import sys
import numpy as np
from csi_processing import load_csi, validate_packet_intervals

def analyze_file(csv_path):
    parsed = load_csi(csv_path)
    host = parsed.time
    fs = validate_packet_intervals(host)
    seq = parsed.records['seq'].astype(np.int64)
    gaps = seq.diff().dropna()
    lost = int((gaps[gaps > 1] - 1).sum())
    expected = int(seq.max() - seq.min() + 1)
    amplitudes = parsed.amplitudes
    variances = np.var(amplitudes, axis=0) if len(amplitudes) > 1 else np.zeros(1)
    return {'file': os.path.basename(csv_path), 'packets': len(parsed.records), 'duration_s': round(float(host[-1]), 2), 'rate_hz': round(fs, 1), 'delivery_pct': round(100 * (1 - lost / max(1, expected)), 2), 'lost_pkts': lost, 'rssi_mean': round(float(parsed.records['rssi'].mean()), 1), 'rssi_std': round(float(parsed.records['rssi'].std()), 2), 'mean_variance': round(float(variances.mean()), 2), 'num_subcarriers': amplitudes.shape[1]}

f1 = sys.argv[1] if len(sys.argv) > 1 else 'data/empty_room_20261112_063039.csv'
f2 = sys.argv[2] if len(sys.argv) > 2 else 'data/person_walking_20261112_063109.csv'
for result in (analyze_file(f1), analyze_file(f2)):
    print(result)
