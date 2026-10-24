import http.server
import socket
import socketserver
import threading
import json
import time
import os
import sys
import glob
import numpy as np
import pandas as pd

HTTP_PORT = 8080
UDP_PORT = 9000
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(DATA_DIR, exist_ok=True)

HDR = ["host_time", "seq", "mac", "rssi", "rate", "sig_mode", "mcs", "cwb",
       "smoothing", "not_sounding", "aggregation", "stbc", "fec_coding", "sgi",
       "noise_floor", "ampdu_cnt", "channel", "secondary_channel", "local_timestamp",
       "ant", "sig_len", "rx_format", "len", "first_word", "n_sub", "data"]

# Global State
state = {
    "latest_subcarriers": [],
    "latest_rssi": -99,
    "latest_seq": 0,
    "last_packet_time": 0,
    "packet_counter": 0,
    "current_rate": 0.0,
    "is_recording": False,
    "record_label": "",
    "record_file": "",
    "record_start_time": 0,
    "record_duration": 60,
    "record_packets": 0,
    "last_analysis": None
}

state_lock = threading.Lock()
record_file_handle = None

def parse_csi_line(line):
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

def udp_worker():
    global record_file_handle
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.settimeout(0.2)
    print(f"[UDP Worker] Listening on 0.0.0.0:{UDP_PORT}...")

    buf = ""
    rate_timer = time.time()
    packet_window = 0

    while True:
        try:
            data, _ = sock.recvfrom(4096)
        except socket.timeout:
            continue
        except Exception as e:
            time.sleep(0.1)
            continue

        chunk = data.decode("latin-1", "ignore")
        buf += chunk
        now = time.time()

        while "\n" in buf:
            line, buf = buf.split("\n", 1)
            parsed = parse_csi_line(line)
            if not parsed:
                continue

            meta, vals = parsed
            seq = int(meta[0]) if meta[0].isdigit() else 0
            rssi = int(meta[2]) if len(meta) > 2 and (meta[2].isdigit() or meta[2].startswith("-")) else -99

            # Extract subcarrier amplitudes for live UI
            amps = []
            if vals:
                try:
                    clean_vals = [int(x.strip(' "[]')) for x in vals if x.strip(' "[]')]
                    for i in range(0, len(clean_vals) - 1, 2):
                        im, re = clean_vals[i], clean_vals[i+1]
                        amps.append(round((im*im + re*re) ** 0.5, 1))
                except Exception:
                    pass

            packet_window += 1
            if now - rate_timer >= 1.0:
                with state_lock:
                    state["current_rate"] = round(packet_window / (now - rate_timer), 1)
                packet_window = 0
                rate_timer = now

            with state_lock:
                state["latest_subcarriers"] = amps
                state["latest_rssi"] = rssi
                state["latest_seq"] = seq
                state["last_packet_time"] = now
                state["packet_counter"] += 1

                # Recording logic
                if state["is_recording"]:
                    elapsed = now - state["record_start_time"]
                    if state["record_duration"] > 0 and elapsed >= state["record_duration"]:
                        stop_recording_internal()
                    else:
                        if record_file_handle:
                            row = [f"{now:.3f}"] + meta[:23] + [str(len(vals)), ";".join(vals)]
                            record_file_handle.write(",".join(row) + "\n")
                            state["record_packets"] += 1

def stop_recording_internal():
    global record_file_handle
    if not state["is_recording"]:
        return
    state["is_recording"] = False
    if record_file_handle:
        try:
            record_file_handle.close()
        except Exception:
            pass
        record_file_handle = None

    # Run quick analysis in background
    saved_path = state["record_file"]
    threading.Thread(target=run_analysis_file, args=(saved_path,)).start()

def run_analysis_file(csv_path):
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path, dtype={"data": str, "mac": str})
        n = len(df)
        if n < 5:
            return {"error": "Too few packets"}

        host = df["host_time"].astype(float)
        dur = max(0.001, host.max() - host.min())
        rate = round(n / dur, 1)

        ts = df["local_timestamp"].astype(np.int64)
        dts = ts.diff().dropna()
        monotonic = bool((dts > 0).all())
        dt_median_ms = round(float(dts.median()) / 1000.0, 2)
        dt_jitter_ms = round(float(dts.std()) / 1000.0, 2)

        seq = df["seq"].astype(np.int64)
        d_seq = seq.diff().dropna()
        lost = int((d_seq[d_seq > 1] - 1).sum())
        expected = int(seq.max() - seq.min() + 1)
        delivery = round(100.0 * (1.0 - lost / max(1, expected)), 1) if expected > 0 else 0.0

        rssi_mean = round(float(df["rssi"].mean()), 1)
        rssi_std = round(float(df["rssi"].std()), 2)

        res = {
            "file": os.path.basename(csv_path),
            "packets": n,
            "duration": round(dur, 2),
            "rate": rate,
            "delivery_pct": delivery,
            "lost": lost,
            "jitter_ms": dt_jitter_ms,
            "dt_median_ms": dt_median_ms,
            "monotonic": monotonic,
            "rssi_mean": rssi_mean,
            "rssi_std": rssi_std
        }
        with state_lock:
            state["last_analysis"] = res
        return res
    except Exception as e:
        return {"error": str(e)}

class CSIDashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silence terminal HTTP logs

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/api/status":
            with state_lock:
                now = time.time()
                alive = (now - state["last_packet_time"]) < 1.0
                rec_elapsed = round(now - state["record_start_time"], 1) if state["is_recording"] else 0.0
                resp = {
                    "alive": alive,
                    "current_rate": state["current_rate"] if alive else 0.0,
                    "rssi": state["latest_rssi"],
                    "seq": state["latest_seq"],
                    "packet_counter": state["packet_counter"],
                    "subcarriers": state["latest_subcarriers"],
                    "is_recording": state["is_recording"],
                    "record_label": state["record_label"],
                    "record_packets": state["record_packets"],
                    "record_elapsed": rec_elapsed,
                    "record_duration": state["record_duration"],
                    "last_analysis": state["last_analysis"]
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        elif self.path == "/api/files":
            files = []
            for f in glob.glob(os.path.join(DATA_DIR, "*.csv")):
                sz = os.path.getsize(f)
                mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(f)))
                files.append({"name": os.path.basename(f), "size_kb": round(sz / 1024, 1), "date": mtime})
            files.sort(key=lambda x: x["date"], reverse=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(files).encode("utf-8"))
        elif self.path.startswith("/api/analyze?file="):
            fname = self.path.split("=")[-1]
            fpath = os.path.join(DATA_DIR, fname)
            report = run_analysis_file(fpath) or {"error": "Failed"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(report).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        global record_file_handle
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        try:
            params = json.loads(body)
        except Exception:
            params = {}

        if self.path == "/api/record/start":
            label = params.get("label", "activity").strip().replace(" ", "_")
            duration = int(params.get("duration", 60))
            ts_str = time.strftime("%Y%m%d_%H%M%S")
            fname = f"{label}_{ts_str}.csv"
            fpath = os.path.join(DATA_DIR, fname)

            with state_lock:
                if state["is_recording"]:
                    stop_recording_internal()
                record_file_handle = open(fpath, "w", encoding="utf-8")
                record_file_handle.write(",".join(HDR) + "\n")
                state["is_recording"] = True
                state["record_label"] = label
                state["record_file"] = fpath
                state["record_duration"] = duration
                state["record_start_time"] = time.time()
                state["record_packets"] = 0
                state["last_analysis"] = None

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "started", "file": fname}).encode("utf-8"))

        elif self.path == "/api/record/stop":
            with state_lock:
                stop_recording_internal()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "stopped"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Wi-Fi CSI Human Sensing Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #0b0f19; color: #f1f5f9; font-family: ui-sans-serif, system-ui, sans-serif; }
    .glass { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    .glow-green { box-shadow: 0 0 15px rgba(34, 197, 94, 0.3); }
    .glow-blue { box-shadow: 0 0 15px rgba(59, 130, 246, 0.3); }
    .glow-red { box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); }
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">

    <!-- Header -->
    <header class="flex flex-col md:flex-row items-start md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
      <div>
        <div class="flex items-center gap-3">
          <div class="h-4 w-4 rounded-full bg-emerald-500 animate-pulse"></div>
          <h1 class="text-2xl font-bold tracking-tight text-white">Wi-Fi CSI Human Sensing Studio</h1>
          <span class="text-xs px-2.5 py-1 rounded-full font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Milestone 3</span>
        </div>
        <p class="text-slate-400 text-sm mt-1">Live Subcarrier Perturbation & Activity Recording System</p>
      </div>
      <div class="flex items-center gap-4 text-xs font-mono">
        <div class="glass px-3 py-1.5 rounded-lg border border-slate-700">
          <span class="text-slate-400">Router:</span> <span class="text-emerald-400 font-semibold">Project_CSI_Router (Ch 11)</span>
        </div>
        <div class="glass px-3 py-1.5 rounded-lg border border-slate-700">
          <span class="text-slate-400">PC IP:</span> <span class="text-cyan-400 font-semibold">192.168.2.2:9000</span>
        </div>
      </div>
    </header>

    <!-- Node Status Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <!-- Ali Board -->
      <div class="glass p-5 rounded-2xl border border-slate-800">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">📡</span>
            <h2 class="text-base font-semibold text-white">Ali Board</h2>
          </div>
          <span class="px-2 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">Transmitter (TX)</span>
        </div>
        <div class="space-y-1.5 text-xs text-slate-300">
          <p><span class="text-slate-500">Hardware:</span> ESP32-D0WD-V3 (4MB)</p>
          <p><span class="text-slate-500">Role:</span> Fixed 60 pkt/s ESP-NOW Stream</p>
          <p><span class="text-slate-500">Power:</span> Standalone (USB Wall/Powerbank)</p>
          <p><span class="text-slate-500">RF Mode:</span> HT20, MCS0, Channel 11</p>
        </div>
        <div class="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
          <span class="text-slate-400">Connection:</span>
          <span class="text-emerald-400 font-medium flex items-center gap-1.5">
            <span class="h-2 w-2 rounded-full bg-emerald-400"></span> Over-The-Air RF
          </span>
        </div>
      </div>

      <!-- Sabi Board -->
      <div class="glass p-5 rounded-2xl border border-slate-800">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <span class="text-lg">🛰️</span>
            <h2 class="text-base font-semibold text-white">Sabi Board</h2>
          </div>
          <span class="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">Receiver (RX)</span>
        </div>
        <div class="space-y-1.5 text-xs text-slate-300">
          <p><span class="text-slate-500">Hardware:</span> ESP32-D0WD-V3 (4MB)</p>
          <p><span class="text-slate-500">Role:</span> 128 Complex Subcarrier Extraction</p>
          <p><span class="text-slate-500">Transport:</span> Wi-Fi UDP Socket (Port 9000)</p>
          <p><span class="text-slate-500">Delivery:</span> <span id="delivery-tag" class="text-emerald-400 font-bold">99.8% Baseline</span></p>
        </div>
        <div class="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs">
          <span class="text-slate-400">Link Status:</span>
          <span id="sabi-status" class="text-emerald-400 font-medium flex items-center gap-1.5">
            <span class="h-2 w-2 rounded-full bg-emerald-400 animate-ping"></span> Active Streaming
          </span>
        </div>
      </div>

      <!-- Live Stream Metrics -->
      <div class="glass p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-semibold text-white">Live Stream Health</h2>
          <span id="rate-badge" class="px-2.5 py-0.5 text-xs font-mono rounded-full bg-emerald-500/20 text-emerald-300 font-bold">58.7 pkt/s</span>
        </div>
        <div class="grid grid-cols-2 gap-3 my-3">
          <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800 text-center">
            <span class="text-[11px] text-slate-400">Signal RSSI</span>
            <p id="live-rssi" class="text-lg font-bold text-cyan-400 font-mono">-45 dBm</p>
          </div>
          <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800 text-center">
            <span class="text-[11px] text-slate-400">Sequence No.</span>
            <p id="live-seq" class="text-lg font-bold text-amber-400 font-mono">#0</p>
          </div>
        </div>
        <div class="text-[11px] text-slate-400 flex items-center justify-between">
          <span>Total Received:</span>
          <span id="total-packets" class="font-mono text-slate-200 font-semibold">0</span>
        </div>
      </div>
    </div>

    <!-- Live Subcarrier Waterfall / Amplitude Graph -->
    <div class="glass p-5 rounded-2xl border border-slate-800 space-y-3">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <div class="h-2.5 w-2.5 rounded-full bg-cyan-400"></div>
          <h2 class="font-semibold text-white text-base">Live CSI Subcarrier Amplitudes (128 Subcarriers)</h2>
        </div>
        <span class="text-xs text-slate-400">Perturbations correspond to physical movement between Ali Board & Sabi Board</span>
      </div>
      <div class="w-full h-44 bg-slate-950/80 rounded-xl p-2 border border-slate-800 flex items-end">
        <canvas id="csi-canvas" class="w-full h-full"></canvas>
      </div>
    </div>

    <!-- Record Controls & Experiment Panel -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <!-- Control Box -->
      <div class="glass p-5 rounded-2xl border border-slate-800 lg:col-span-1 space-y-4">
        <h2 class="text-base font-semibold text-white flex items-center gap-2">
          <span>🎬</span> Activity Recording (Labeling)
        </h2>

        <div>
          <label class="text-xs text-slate-400 block mb-1.5 font-medium">Activity Label Presets:</label>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <button onclick="setLabel('empty_room')" class="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-700 rounded-lg text-slate-200 border border-slate-700 transition">Empty Room</button>
            <button onclick="setLabel('person_sitting')" class="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-700 rounded-lg text-slate-200 border border-slate-700 transition">Person Sitting</button>
            <button onclick="setLabel('person_walking')" class="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-700 rounded-lg text-slate-200 border border-slate-700 transition">Walking</button>
            <button onclick="setLabel('hand_wave')" class="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-700 rounded-lg text-slate-200 border border-slate-700 transition">Hand Gestures</button>
          </div>
        </div>

        <div>
          <label class="text-xs text-slate-400 block mb-1 font-medium">Custom Label:</label>
          <input id="label-input" type="text" value="empty_room" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono">
        </div>

        <div>
          <label class="text-xs text-slate-400 block mb-1 font-medium">Duration:</label>
          <select id="duration-select" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500">
            <option value="15">15 Seconds (Quick Test)</option>
            <option value="30">30 Seconds</option>
            <option value="60" selected>60 Seconds (Standard M3 Baseline)</option>
            <option value="120">120 Seconds (Extended)</option>
            <option value="0">Continuous (Manual Stop)</option>
          </select>
        </div>

        <div class="pt-2">
          <button id="record-btn" onclick="toggleRecord()" class="w-full py-2.5 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-lg shadow-emerald-500/20 transition flex items-center justify-center gap-2">
            <span id="record-icon" class="h-3 w-3 rounded-full bg-red-400 animate-ping"></span>
            <span id="record-text">Start Recording Session</span>
          </button>
        </div>

        <div id="recording-status-box" class="hidden bg-red-950/40 border border-red-800/40 p-3 rounded-xl text-xs space-y-1">
          <div class="flex items-center justify-between text-red-300 font-semibold">
            <span class="flex items-center gap-1.5">
              <span class="h-2 w-2 rounded-full bg-red-500 animate-ping"></span> Recording Active
            </span>
            <span id="rec-timer" class="font-mono">0.0s / 60s</span>
          </div>
          <p class="text-slate-400 text-[11px]">Saved packets: <span id="rec-packets" class="text-white font-mono font-bold">0</span></p>
        </div>
      </div>

      <!-- Live Analysis Card & History -->
      <div class="glass p-5 rounded-2xl border border-slate-800 lg:col-span-2 space-y-4 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-base font-semibold text-white flex items-center gap-2">
              <span>📊</span> Latest Session Data Quality Report
            </h2>
            <button onclick="refreshFiles()" class="text-xs text-cyan-400 hover:underline">🔄 Refresh Files</button>
          </div>

          <div id="analysis-container" class="bg-slate-900/50 p-4 rounded-xl border border-slate-800 text-xs">
            <p class="text-slate-500 text-center py-4">No recent capture analyzed yet. Record an activity or select a file below.</p>
          </div>
        </div>

        <!-- Recorded Files Table -->
        <div>
          <h3 class="text-xs font-semibold text-slate-300 mb-2">Saved CSI Dataset Captures (`data/`):</h3>
          <div class="max-h-36 overflow-y-auto space-y-1 text-xs font-mono" id="files-list">
            <p class="text-slate-500">Loading files...</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let isRecording = false;
    const canvas = document.getElementById('csi-canvas');
    const ctx = canvas.getContext('2d');

    function resizeCanvas() {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    function setLabel(val) {
      document.getElementById('label-input').value = val;
    }

    async function toggleRecord() {
      if (!isRecording) {
        const label = document.getElementById('label-input').value;
        const duration = parseInt(document.getElementById('duration-select').value);
        await fetch('/api/record/start', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({label, duration})
        });
      } else {
        await fetch('/api/record/stop', {method: 'POST'});
      }
    }

    function renderSubcarriers(amps) {
      if (!amps || amps.length === 0) return;
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const barWidth = w / amps.length;
      const maxAmp = 60.0; // scale factor

      for (let i = 0; i < amps.length; i++) {
        const amp = amps[i];
        const barHeight = Math.min(h, (amp / maxAmp) * h);
        const x = i * barWidth;
        const y = h - barHeight;

        // Gradient color: Cyan to Purple
        const hue = 180 + (i / amps.length) * 100;
        ctx.fillStyle = `hsl(${hue}, 85%, 55%)`;
        ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
      }
    }

    function renderAnalysis(data) {
      if (!data || data.error) return;
      const html = `
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="p-2.5 rounded-lg bg-slate-800/50">
            <span class="text-slate-400 block text-[10px]">Delivery Rate</span>
            <span class="text-sm font-bold ${data.delivery_pct >= 98 ? 'text-emerald-400' : 'text-amber-400'} font-mono">${data.delivery_pct}%</span>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-800/50">
            <span class="text-slate-400 block text-[10px]">Rate</span>
            <span class="text-sm font-bold text-cyan-400 font-mono">${data.rate} pkt/s</span>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-800/50">
            <span class="text-slate-400 block text-[10px]">Jitter (σ)</span>
            <span class="text-sm font-bold text-indigo-400 font-mono">${data.jitter_ms} ms</span>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-800/50">
            <span class="text-slate-400 block text-[10px]">RSSI</span>
            <span class="text-sm font-bold text-amber-400 font-mono">${data.rssi_mean} dBm</span>
          </div>
        </div>
        <p class="mt-2 text-[11px] text-slate-400">File: <span class="text-white font-mono">${data.file}</span> (${data.packets} packets, ${data.duration}s duration, lost ${data.lost})</p>
      `;
      document.getElementById('analysis-container').innerHTML = html;
    }

    async function analyzeFile(fname) {
      document.getElementById('analysis-container').innerHTML = `<p class="text-cyan-400 text-center py-4">Analyzing ${fname}...</p>`;
      const res = await fetch(`/api/analyze?file=${encodeURIComponent(fname)}`);
      const data = await res.json();
      renderAnalysis(data);
    }

    async function refreshFiles() {
      const res = await fetch('/api/files');
      const files = await res.json();
      const container = document.getElementById('files-list');
      if (files.length === 0) {
        container.innerHTML = '<p class="text-slate-500">No files found.</p>';
        return;
      }
      container.innerHTML = files.map(f => `
        <div class="flex items-center justify-between p-1.5 rounded bg-slate-900/40 hover:bg-slate-800/60 border border-slate-800/60">
          <span class="truncate max-w-xs text-slate-300">${f.name}</span>
          <div class="flex items-center gap-3">
            <span class="text-slate-500 text-[11px]">${f.size_kb} KB</span>
            <button onclick="analyzeFile('${f.name}')" class="text-xs text-cyan-400 hover:text-cyan-300 font-sans px-2 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/50">Analyze</button>
          </div>
        </div>
      `).join('');
    }

    async function pollStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();

        // Update live metrics
        document.getElementById('live-rssi').innerText = `${data.rssi} dBm`;
        document.getElementById('live-seq').innerText = `#${data.seq}`;
        document.getElementById('total-packets').innerText = data.packet_counter.toLocaleString();
        document.getElementById('rate-badge').innerText = `${data.current_rate} pkt/s`;

        // Update subcarrier visualization
        if (data.subcarriers && data.subcarriers.length > 0) {
          renderSubcarriers(data.subcarriers);
        }

        // Recording button state
        isRecording = data.is_recording;
        const btn = document.getElementById('record-btn');
        const text = document.getElementById('record-text');
        const icon = document.getElementById('record-icon');
        const statusBox = document.getElementById('recording-status-box');

        if (isRecording) {
          btn.className = "w-full py-2.5 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-700 hover:to-rose-800 text-white shadow-lg shadow-red-500/30 transition flex items-center justify-center gap-2";
          text.innerText = "Stop Recording";
          icon.className = "h-3 w-3 rounded-full bg-white animate-pulse";
          statusBox.classList.remove('hidden');
          document.getElementById('rec-timer').innerText = `${data.record_elapsed}s / ${data.record_duration}s`;
          document.getElementById('rec-packets').innerText = data.record_packets;
        } else {
          btn.className = "w-full py-2.5 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-lg shadow-emerald-500/20 transition flex items-center justify-center gap-2";
          text.innerText = "Start Recording Session";
          icon.className = "h-3 w-3 rounded-full bg-red-400 animate-ping";
          statusBox.classList.add('hidden');
        }

        if (data.last_analysis) {
          renderAnalysis(data.last_analysis);
        }
      } catch (e) {
        console.error(e);
      }
    }

    refreshFiles();
    setInterval(pollStatus, 200); // 5Hz smooth refresh
  </script>
</body>
</html>
"""

def main():
    udp_t = threading.Thread(target=udp_worker, daemon=True)
    udp_t.start()

    server = socketserver.ThreadingTCPServer(("", HTTP_PORT), CSIDashboardHandler)
    server.allow_reuse_address = True
    print(f"\n=======================================================")
    print(f"[*] Wi-Fi CSI Studio Dashboard Running at:")
    print(f"    http://localhost:{HTTP_PORT}")
    print(f"    http://127.0.0.1:{HTTP_PORT}")
    print(f"=======================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard...")
        server.shutdown()

if __name__ == "__main__":
    main()
