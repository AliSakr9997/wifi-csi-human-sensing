import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from csi_processing import load_csi, validate_packet_intervals

def load_and_filter(csv_path):
    parsed = load_csi(csv_path)
    fs = validate_packet_intervals(parsed.time)
    nyq = 0.5 * fs
    b, a = butter(4, [0.2 / nyq, 10.0 / nyq], btype='band')
    return parsed.time, parsed.amplitudes, filtfilt(b, a, parsed.amplitudes, axis=0)

f_empty = r'C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data\empty_room_20261112_063039.csv'
f_walk = r'C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\data\person_walking_20261112_063109.csv'
t_empty, amplitudes_empty, filtered_empty = load_and_filter(f_empty)
t_walk, amplitudes_walk, filtered_walk = load_and_filter(f_walk)
top_sub = int(np.argmax(np.var(amplitudes_walk, axis=0)))
fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=False)
axes[0].plot(t_empty, amplitudes_empty[:, top_sub], label='Empty room')
axes[0].plot(t_walk, amplitudes_walk[:, top_sub], label='Walking'); axes[0].set_title('Raw CSI amplitude'); axes[0].legend()
axes[1].plot(t_empty, filtered_empty[:, top_sub], label='Empty room')
axes[1].plot(t_walk, filtered_walk[:, top_sub], label='Walking'); axes[1].set_title('Validated-rate bandpass (0.2-10 Hz)'); axes[1].legend()
indices = np.arange(1, amplitudes_empty.shape[1] + 1)
axes[2].bar(indices - .2, np.var(amplitudes_empty, axis=0), width=.4, label='Empty room')
axes[2].bar(indices + .2, np.var(amplitudes_walk, axis=0), width=.4, label='Walking'); axes[2].set_title('Temporal variance'); axes[2].legend()
plt.tight_layout(); plt.savefig('docs/live_validation_test.png', dpi=150, bbox_inches='tight')
