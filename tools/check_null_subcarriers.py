import os
import numpy as np
from csi_processing import load_csi

path = os.path.join('data', 'empty_room_20261112_063039.csv')
parsed = load_csi(path)
means = parsed.amplitudes.mean(axis=0)
null_indices = np.where(means < 1.0)[0]
active_indices = np.where(means >= 1.0)[0]
print(f'Total subcarriers evaluated: {len(means)}')
print(f'Null / Zero energy subcarriers (count={len(null_indices)}): {null_indices.tolist()}')
print(f'Active carrier count: {len(active_indices)}')
print(f'Active amplitude range: {means[active_indices].min():.1f} to {means[active_indices].max():.1f}')
