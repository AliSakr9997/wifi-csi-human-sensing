import sys, numpy as np, pandas as pd

CSV = sys.argv[1] if len(sys.argv) > 1 else "data/csi_run1.csv"
N_SAMPLE = 600  # packets sampled for amplitude stats

df = pd.read_csv(CSV, dtype={"data": str, "mac": str})
n = len(df)
print(f"file: {CSV}")
print(f"packets: {n}")

# ---- time / rate
host = df["host_time"].astype(float)
dur = host.max() - host.min()
print(f"host duration: {dur:.2f} s   -> rate {n/dur:.1f} pkt/s")

ts = df["local_timestamp"].astype(np.int64)
dts = ts.diff().dropna()
print(f"device timestamp: monotonic = {bool((dts > 0).all())}   "
      f"non-monotonic steps = {int((dts <= 0).sum())}")
print(f"device dt (us): median {dts.median():.0f}  mean {dts.mean():.0f}  std {dts.std():.0f} "
      f"min {dts.min():.0f}  max {dts.max():.0f}  -> {1e6/dts.median():.1f} pkt/s")
big = int((dts > 3 * dts.median()).sum())
print(f"gaps > 3x median interval: {big}  (max gap {dts.max()/1000:.1f} ms)")

# ---- sender sequence => true loss
seq = df["seq"].astype(np.int64)
d_seq = seq.diff().dropna()
lost = int((d_seq[d_seq > 1] - 1).sum())
print(f"sender seq: {seq.min()}..{seq.max()}   expected {int(seq.max()-seq.min()+1)}   "
      f"lost {lost}  -> delivered {100*(1-lost/(seq.max()-seq.min()+1)):.1f}%")

# ---- radio / fixed fields
print("\n-- fixed fields (unique values) --")
for c in ["mac", "rate", "sig_mode", "mcs", "cwb", "smoothing", "not_sounding",
          "aggregation", "stbc", "fec_coding", "sgi", "channel",
          "secondary_channel", "len", "n_sub", "first_word", "ant", "rx_format"]:
    if c in df.columns:
        u = df[c].unique()
        print(f"  {c:18s}: {list(u)[:6]}{' ...' if len(u) > 6 else ''}")

print("\n-- power --")
print(f"  rssi        : min {df['rssi'].min()}  max {df['rssi'].max()}  "
      f"mean {df['rssi'].mean():.1f}  std {df['rssi'].std():.2f}")
print(f"  noise_floor : {sorted(df['noise_floor'].unique())}")
print(f"  first_word_invalid (first_word==1): {int((df['first_word'] == 1).sum())}/{n}")

# ---- csi payload sanity
nsub = df["n_sub"].astype(int)
print(f"\ncsi payload: n_sub min {nsub.min()} max {nsub.max()} (constant={nsub.nunique()==1})")
print(f"  => {nsub.iloc[0]} int8 samples = {nsub.iloc[0]//2} complex subcarriers (imag,real pairs)")

amps = []
for s in df["data"].head(N_SAMPLE):
    v = np.fromstring(s, sep=";", dtype=np.float32)
    if v.size % 2 == 0 and v.size:
        iq = v.reshape(-1, 2).astype(np.float32)
        amps.append(np.sqrt((iq ** 2).sum(axis=1)))
if amps:
    A = np.vstack(amps)
    print(f"  amplitude over {len(amps)} packets x {A.shape[1]} subcarriers:")
    print(f"    overall mean {A.mean():.1f}  std {A.std():.1f}  "
          f"min {A.min():.1f}  max {A.max():.1f}")
    print(f"    per-subcarrier mean range: {A.mean(axis=0).min():.1f} .. {A.mean(axis=0).max():.1f}")
    print(f"    packets with all-zero payload: "
          f"{int((A.sum(axis=1) == 0).sum())}")
