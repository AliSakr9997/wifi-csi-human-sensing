import sys
import numpy as np
import pandas as pd
from csi_processing import parse_csi_records, validate_packet_intervals

CSV = sys.argv[1] if len(sys.argv) > 1 else 'data/csi_run1.csv'
N_SAMPLE = 600
df = pd.read_csv(CSV, dtype={'data': str, 'mac': str})
parsed = parse_csi_records(df)
print(f'file: {CSV}')
print(f'packets: {len(parsed.records)}')
fs = validate_packet_intervals(parsed.time)
print(f'validated host sampling rate: {fs:.1f} pkt/s')
local = parsed.records['local_timestamp'].astype(np.int64).diff().dropna()
print(f'device timestamp: monotonic = {bool((local > 0).all())} non-monotonic steps = {int((local <= 0).sum())}')
print(f'device dt (us): median {local.median():.0f} mean {local.mean():.0f} std {local.std():.0f} min {local.min():.0f} max {local.max():.0f}')
seq = parsed.records['seq'].astype(np.int64)
gaps = seq.diff().dropna(); lost = int((gaps[gaps > 1] - 1).sum()); expected = int(seq.max() - seq.min() + 1)
print(f'sender seq: {seq.min()}..{seq.max()} expected {expected} lost {lost} -> delivered {100 * (1 - lost / max(1, expected)):.1f}%')
for column in ['mac', 'rate', 'sig_mode', 'mcs', 'cwb', 'channel', 'n_sub', 'first_word']:
    if column in parsed.records: print(f'  {column:18s}: {list(parsed.records[column].unique())[:6]}')
print(f"first_word_invalid (first_word==1): {int((parsed.records['first_word'] == 1).sum())}/{len(parsed.records)}")
amplitudes = parsed.amplitudes[:N_SAMPLE]
print(f'amplitude over {len(amplitudes)} packets x {amplitudes.shape[1]} subcarriers:')
print(f'  overall mean {amplitudes.mean():.1f} std {amplitudes.std():.1f} min {amplitudes.min():.1f} max {amplitudes.max():.1f}')
