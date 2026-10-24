import os
import pandas as pd
import numpy as np

files = [
    'empty_room_20261024_035317.csv',
    'person_sitting_20261024_034928.csv',
    'person_walking_20261024_035105.csv',
    'hand_wave_20261024_035248.csv'
]

print(f"{'Activity File':<36} | {'Packets':>7} | {'Dur (s)':>7} | {'Rate':>6} | {'Delivery':>8} | {'Jitter':>7} | {'RSSI':>7}")
print("-" * 88)

for fn in files:
    path = os.path.join('data', fn)
    if not os.path.exists(path):
        continue
    df = pd.read_csv(path, dtype={'data': str, 'mac': str})
    n = len(df)
    host = df['host_time'].astype(float)
    dur = round(float(host.max() - host.min()), 1)
    rate = round(n / max(0.001, dur), 1)
    ts = df['local_timestamp'].astype(np.int64)
    dts = ts.diff().dropna()
    jitter = round(float(dts.std()) / 1000.0, 2)
    seq = df['seq'].astype(np.int64)
    d_seq = seq.diff().dropna()
    lost = int((d_seq[d_seq > 1] - 1).sum())
    expected = int(seq.max() - seq.min() + 1)
    delivery = round(100.0 * (1.0 - lost / max(1, expected)), 1)
    rssi_mean = round(float(df['rssi'].mean()), 1)
    print(f"{fn:<36} | {n:>7} | {dur:>7.1f} | {rate:>6.1f} | {delivery:>7.1f}% | {jitter:>5.2f}ms | {rssi_mean:>5.1f}dBm")
