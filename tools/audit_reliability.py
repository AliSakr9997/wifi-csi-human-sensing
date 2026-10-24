import os
import glob
import pandas as pd
import numpy as np

def audit_file(csv_path):
    print("=" * 80)
    print(f"AUDITING: {os.path.basename(csv_path)}")
    print("=" * 80)
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f if line.strip()]
        
    if not lines:
        print("[!] File is empty.")
        return
        
    header = lines[0].split(',')
    print(f"Header ({len(header)} cols): {header[:6]} ... {header[-4:]}")
    
    malformed_rows = 0
    subcarrier_counts = set()
    first_word_invalids = set()
    
    host_times = []
    local_ts = []
    seq_ids = []
    rssis = []
    
    for idx, line in enumerate(lines[1:], start=2):
        parts = line.split(',')
        if len(parts) < 26:
            malformed_rows += 1
            continue
            
        try:
            h_time = float(parts[0])
            s_id = int(parts[1])
            rssi = int(parts[3])
            l_ts = int(parts[18])
            fw_invalid = int(parts[23])
            raw_data = parts[25].strip(' "')
            
            host_times.append(h_time)
            seq_ids.append(s_id)
            rssis.append(rssi)
            local_ts.append(l_ts)
            first_word_invalids.add(fw_invalid)
            
            sub_vals = [x for x in raw_data.split(';') if x.strip()]
            subcarrier_counts.add(len(sub_vals))
        except Exception as e:
            malformed_rows += 1
            
    n = len(seq_ids)
    print(f"Total Rows Parsed: {n} | Malformed Rows: {malformed_rows}")
    print(f"Subcarrier Value Counts observed: {subcarrier_counts}")
    print(f"First-word-invalid flags observed: {first_word_invalids}")
    
    if n < 5:
        print("[!] Too few rows to analyze sequence.")
        return
        
    # Sequence analysis
    seq = np.array(seq_ids)
    d_seq = np.diff(seq)
    
    duplicates = int(np.sum(d_seq == 0))
    out_of_order = int(np.sum(d_seq < 0))
    gaps = int(np.sum(d_seq > 1))
    lost_packets = int(np.sum(d_seq[d_seq > 1] - 1)) if gaps > 0 else 0
    expected_packets = int(seq[-1] - seq[0] + 1)
    delivery_pct = 100.0 * (1.0 - lost_packets / max(1, expected_packets)) if expected_packets > 0 else 100.0
    
    print(f"Sequence Range: [{seq[0]} -> {seq[-1]}] (Span: {expected_packets})")
    print(f"Duplicates: {duplicates} | Out-of-order: {out_of_order}")
    print(f"Gaps (Drops): {gaps} | Total Lost: {lost_packets} | Delivery: {delivery_pct:.2f}%")
    
    # Timing analysis
    ht = np.array(host_times)
    d_ht = np.diff(ht) * 1000.0  # ms
    
    lt = np.array(local_ts, dtype=np.int64)
    d_lt = np.diff(lt) / 1000.0  # ms
    
    host_dur = ht[-1] - ht[0]
    local_dur = (lt[-1] - lt[0]) / 1000000.0
    
    print(f"Host Duration: {host_dur:.2f} s | On-Chip Local Duration: {local_dur:.2f} s")
    drift_ms = abs(host_dur - local_dur) * 1000.0
    drift_ppm = (abs(host_dur - local_dur) / max(0.001, host_dur)) * 1e6
    print(f"Clock Drift: {drift_ms:.2f} ms over {host_dur:.1f} s ({drift_ppm:.1f} ppm)")
    print(f"Interval Median: Host = {np.median(d_ht):.2f} ms | ESP32 = {np.median(d_lt):.2f} ms")
    print(f"Interval Jitter (StdDev): Host = {np.std(d_ht):.2f} ms | ESP32 = {np.std(d_lt):.2f} ms")
    print(f"Host Monotonic: {bool(np.all(d_ht > 0))} | Local Monotonic: {bool(np.all(d_lt > 0))}")
    print(f"RSSI: Mean = {np.mean(rssis):.1f} dBm, Min = {np.min(rssis)} dBm, Max = {np.max(rssis)} dBm\n")

if __name__ == "__main__":
    for f in sorted(glob.glob('data/*.csv')):
        if 'run1' in f: continue  # skip serial fail test
        audit_file(f)
