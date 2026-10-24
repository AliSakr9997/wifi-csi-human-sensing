import pandas as pd
import numpy as np

df = pd.read_csv('data/csi_udp_ht20_60hz.csv')
ht = df['host_time'].values
d_ht = np.diff(ht)
non_mono = np.where(d_ht <= 0)[0]
print(f'Count of non-monotonic host timestamps: {len(non_mono)}')
for idx in non_mono[:10]:
    print(f'Row {idx}: ht={ht[idx]:.4f}, next_ht={ht[idx+1]:.4f}, diff={d_ht[idx]*1000:.3f}ms, seq={df["seq"].values[idx]}->{df["seq"].values[idx+1]}')
