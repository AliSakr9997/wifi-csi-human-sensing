import pandas as pd
import numpy as np

df = pd.read_csv(r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data\empty_room_20261112_063039.csv", nrows=100)
amps = []
for s in df['data']:
    raw_str = str(s).strip(' "[]')
    sep = ';' if ';' in raw_str else ','
    vals = [int(x.strip()) for x in raw_str.split(sep) if x.strip()]
    a = [np.sqrt(vals[i]**2 + vals[i+1]**2) for i in range(0, len(vals)-1, 2)]
    amps.append(a[1:]) # skip index 0

A = np.array(amps)
means = A.mean(axis=0)
null_indices = np.where(means < 1.0)[0]
active_indices = np.where(means >= 1.0)[0]

print(f"Total subcarriers evaluated: {len(means)}")
print(f"Null / Zero energy subcarriers (count={len(null_indices)}): {null_indices.tolist()}")
print(f"Active carrier count: {len(active_indices)}")
print(f"Active amplitude range: {means[active_indices].min():.1f} to {means[active_indices].max():.1f}")
