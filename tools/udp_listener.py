import socket, sys, time, csv, os

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
OUT = sys.argv[3] if len(sys.argv) > 3 else "csi_capture_udp.csv"
BIND = sys.argv[4] if len(sys.argv) > 4 else "0.0.0.0"

HDR = ["host_time", "seq", "mac", "rssi", "rate", "sig_mode", "mcs", "cwb",
       "smoothing", "not_sounding", "aggregation", "stbc", "fec_coding", "sgi",
       "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
       "ant", "sig_len", "rx_format", "len", "first_word", "n_sub", "data"]

def parse(line):
    line = line.strip()
    if not line.startswith("CSI_DATA,"):
        return None
    bi = line.find(',"[')
    if bi < 0:
        return None
    meta = line[len("CSI_DATA,"):bi].split(",")
    arr = line[bi + 2:].strip().strip('"')
    if arr.startswith("[") and arr.endswith("]"):
        arr = arr[1:-1]
    vals = arr.split(",") if arr else []
    if len(meta) < 23:
        return None
    return meta, vals

def main():
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((BIND, PORT))
    s.settimeout(0.2)
    print(f"[capture-udp] {BIND}:{PORT} for {SECS}s -> {OUT}", flush=True)
    t0 = time.time()
    n = 0
    buf = ""
    f = open(OUT, "w", newline="", encoding="utf-8")
    w = csv.writer(f)
    w.writerow(HDR)
    while time.time() - t0 < SECS:
        try:
            data, addr = s.recvfrom(4096)
        except socket.timeout:
            continue
        chunk = data.decode("latin-1", "ignore")
        buf += chunk
        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            p = parse(line)
            if not p:
                continue
            meta, vals = p
            w.writerow([f"{time.time():.3f}"] + meta[:23] + [len(vals), ";".join(vals)])
            n += 1
            if n % 200 == 0:
                print(f"[capture-udp] {n} packets ({time.time()-t0:.0f}s)", flush=True)
    f.close()
    s.close()
    print(f"[capture-udp] DONE: {n} CSI packets -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
