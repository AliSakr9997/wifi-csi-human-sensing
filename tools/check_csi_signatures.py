import os
import numpy as np
from csi_processing import load_csi

files = {'Empty Room': 'empty_room_20261024_035317.csv', 'Person Sitting': 'person_sitting_20261024_034928.csv', 'Person Walking': 'person_walking_20261024_035105.csv', 'Hand Wave': 'hand_wave_20261024_035248.csv'}

def extract_amp_matrix(csv_path):
    return load_csi(csv_path).amplitudes

print(f"{'Activity':<16} | {'Shape (Pkts x Subs)':<20} | {'Mean Amplitude':<15} | {'Mean Variance':<15} | {'Std Dev':<10}")
print('-' * 85)
for label, filename in files.items():
    matrix = extract_amp_matrix(os.path.join('data', filename))
    variance = np.var(matrix, axis=0)
    mean_variance = float(np.mean(variance))
    print(f"{label:<16} | {str(matrix.shape):<20} | {np.mean(matrix):<15.2f} | {mean_variance:<15.3f} | {np.sqrt(mean_variance):<10.3f}")
