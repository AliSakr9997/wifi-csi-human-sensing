import os
import pandas as pd
import numpy as np

files = {
    'Empty Room': 'empty_room_20261024_035317.csv',
    'Person Sitting': 'person_sitting_20261024_034928.csv',
    'Person Walking': 'person_walking_20261024_035105.csv',
    'Hand Wave': 'hand_wave_20261024_035248.csv'
}

def extract_amp_matrix(csv_path):
    df = pd.read_csv(csv_path, dtype={'data': str})
    # data column contains semicolon-separated integers
    amps_list = []
    for raw in df['data']:
        if not isinstance(raw, str):
            continue
        parts = [p.strip(' "[]') for p in raw.split(';') if p.strip(' "[]')]
        try:
            ints = [int(p) for p in parts]
            # convert complex pairs (imag, real) to amplitude
            # ESP32 CSI format: [imag0, real0, imag1, real1, ...]
            # Note: subcarrier index 0 is first_word_invalid per ESP-CSI docs
            amps = []
            for i in range(2, len(ints) - 1, 2):  # skip subcarrier 0 (first word)
                im, re = ints[i], ints[i+1]
                amps.append(np.sqrt(im*im + re*re))
            if len(amps) > 10:
                amps_list.append(amps)
        except Exception:
            continue
    return np.array(amps_list)

print(f"{'Activity':<16} | {'Shape (Pkts x Subs)':<20} | {'Mean Amplitude':<15} | {'Mean Variance':<15} | {'Std Dev':<10}")
print("-" * 85)

for label, fn in files.items():
    path = os.path.join('data', fn)
    mat = extract_amp_matrix(path)
    if len(mat) == 0:
        continue
    # Compute variance across time (axis=0) for each subcarrier, then average over subcarriers
    var_per_sub = np.var(mat, axis=0)
    mean_var = float(np.mean(var_per_sub))
    mean_amp = float(np.mean(mat))
    std_dev = float(np.sqrt(mean_var))
    print(f"{label:<16} | {str(mat.shape):<20} | {mean_amp:<15.2f} | {mean_var:<15.3f} | {std_dev:<10.3f}")
