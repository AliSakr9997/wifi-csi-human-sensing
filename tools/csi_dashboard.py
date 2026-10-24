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
    arr = line[bi + 2:].strip()
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
        except Exception:
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

HTML_PAGE = """<!doctype html>
<html lang="en">

<head>
   <meta charset="UTF-8">
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   <title>Wi-Fi CSI Sensing Studio — AI Human Activity Hub</title>
   <meta name="description" content="Real-time Wi-Fi CSI sensing, human presence and activity detection hub.">
   <script src='https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4'></script>
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link
      href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap"
      rel="stylesheet">
   <style>
      :root {
         color-scheme: light only;
      }

      body {
         font-family: 'Inter', sans-serif;
      }

      @keyframes app-marquee {
         0% {
            transform: translateX(0);
         }
         100% {
            transform: translateX(-50%);
         }
      }

      @media (prefers-reduced-motion: reduce) {
         @keyframes app-marquee {
            0%, 100% {
               transform: translateX(0);
            }
         }
      }
   </style>
</head>

<body class="max-w-[1920px] mx-auto text-slate-900 text-base bg-white">
   <!-- ─── NAVBAR ─── -->
   <nav
      class="flex py-2 px-4 md:px-8 bg-white/90 border-b border-slate-300 min-h-[68px] fixed top-0 w-full z-30 transition-all lg:backdrop-blur-md"
      aria-label="Main navigation">
      <div class="max-w-7xl mx-auto flex items-center justify-between flex-wrap gap-4 w-full">

         <!-- Logo -->
         <a href="#live-studio" aria-label="Wi-Fi CSI Sensing Studio – home" aria-current="page"
            class="flex items-center gap-2.5 rounded shrink-0 focus:outline-none focus-visible:ring-2 ring-offset-2 focus-visible:ring-blue-500">
            <div
               class="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-blue-600 via-indigo-600 to-violet-600 shadow-sm shadow-blue-500/20">
               <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12.55a11 11 0 0 1 14.08 0"></path>
                  <path d="M1.42 9a16 16 0 0 1 21.16 0"></path>
                  <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
                  <circle cx="12" cy="20" r="1.5" fill="currentColor"></circle>
               </svg>
            </div>
            <div>
               <div class="flex items-center gap-2">
                  <span class="font-bold text-base text-slate-900 tracking-tight">CSI Sensing Hub</span>
                  <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">M3 Verified</span>
               </div>
               <span class="text-[11px] text-slate-500 block -mt-0.5">Ali Board & Sabi Board</span>
            </div>
         </a>

         <!-- Nav links -->
         <div id="collapseMenu" tabindex="-1"
            class="hidden z-50 outline-none lg:block max-lg:bg-white max-lg:border-l max-lg:border-slate-300 max-lg:w-1/2 max-lg:fixed max-lg:top-0 max-lg:right-0 max-lg:h-full max-lg:shadow-md max-lg:overflow-auto max-sm:w-full">

            <div class="py-4 px-5 flex justify-between items-center border-b border-slate-100 sticky top-0 bg-white z-50 lg:hidden">
               <div class="flex items-center gap-2">
                  <div class="w-7 h-7 rounded-md flex items-center justify-center bg-gradient-to-br from-blue-600 to-violet-600">
                     <svg class="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="20" r="1.5" fill="currentColor"></circle>
                     </svg>
                  </div>
                  <span class="font-bold text-slate-900">CSI Sensing Hub</span>
               </div>
               <button type="button" aria-controls="collapseMenu" id="toggleClose"
                  class="cursor-pointer w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 focus:outline-none">
                  <svg class="w-4 h-4 text-slate-700" viewBox="0 0 16 16" fill="none">
                     <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  </svg>
               </button>
            </div>

            <ul class="flex flex-col lg:flex-row lg:items-center gap-7 max-lg:p-5">
               <li>
                  <a href="#live-studio" class="text-sm font-semibold hover:text-blue-700 transition-colors">
                     Live Studio
                  </a>
               </li>
               <li>
                  <a href="#hardware-nodes" class="text-sm font-semibold hover:text-blue-700 transition-colors">
                     Hardware Nodes
                  </a>
               </li>
               <li>
                  <a href="#benchmarks" class="text-sm font-semibold hover:text-blue-700 transition-colors">
                     Data Quality
                  </a>
               </li>
               <li>
                  <a href="#datasets" class="text-sm font-semibold hover:text-blue-700 transition-colors">
                     Recorded Datasets
                  </a>
               </li>
               <li>
                  <a href="#faq" class="text-sm font-semibold hover:text-blue-700 transition-colors">
                     FAQ
                  </a>
               </li>
            </ul>
         </div>

         <!-- Status Badge & Quick Controls -->
         <div class="flex items-center gap-3 shrink-0">
            <div class="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800">
               <span class="relative flex h-2 w-2">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
               </span>
               <span id="nav-rate">58.8 pkt/s</span>
               <span class="text-emerald-400">&bull;</span>
               <span>UDP: 9000</span>
            </div>

            <a href="#live-studio"
               class="py-2.5 px-4 text-sm flex items-center gap-1.5 rounded-full font-semibold text-white border border-blue-600 bg-blue-600 hover:bg-blue-700 transition-all shadow-sm">
               Open Studio
               <svg xmlns="http://www.w3.org/2000/svg" class="size-3.5 fill-current" viewBox="0 0 466.205 466.205">
                  <path d="m295.311 416.193.158-.158 163.2-162.986a25.4 25.4 0 0 0 3.413-4.267l2.56-4.693 1.067-3.2v-2.347a30.1 30.1 0 0 0 0-10.88v-4.693l-1.92-3.627a25.8 25.8 0 0 0-4.053-5.547L295.47 50.17c-10.87-10.957-28.565-11.028-39.522-.158l-.158.158c-10.538 11.045-10.538 28.421 0 39.467l97.28 97.493c4.124 4.206 4.058 10.96-.149 15.084a10.66 10.66 0 0 1-7.318 3.05H27.95C12.514 205.26.001 217.772 0 233.206c0 15.435 12.51 27.947 27.945 27.95h317.657c5.89.082 10.6 4.924 10.516 10.814a10.67 10.67 0 0 1-3.049 7.318l-97.28 97.067c-10.674 11.073-10.674 28.607 0 39.68 10.87 10.957 28.565 11.028 39.522.157" />
               </svg>
            </a>

            <button type="button" aria-controls="collapseMenu" id="toggleOpen"
               class="cursor-pointer lg:hidden flex items-center justify-center p-2 rounded-lg hover:bg-slate-100">
               <svg class="size-6 fill-slate-900" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"></path>
               </svg>
            </button>
         </div>

      </div>
   </nav>

   <main id="main-content">
      <!-- ─── HERO & LIVE STUDIO ─── -->
      <section id="live-studio" class="pb-12 pt-28 md:pb-16 md:pt-36 bg-gradient-to-b from-slate-50 via-white to-slate-50 border-b border-slate-200">
         <div class="px-4 md:px-8 max-w-7xl mx-auto">
            
            <!-- Headline -->
            <div class="max-w-4xl mx-auto text-center mb-10">
               <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100 text-blue-800 text-xs font-semibold mb-4 border border-blue-200">
                  <span>⚡</span> Live Hardware Streaming Active
               </div>
               <h1 class="text-4xl font-semibold !leading-tight mb-4 md:text-5xl lg:text-6xl text-slate-900">
                  Camera-free human sensing.<br />
                  <span class="text-blue-600 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-violet-600">Powered by Wi-Fi CSI signals.</span>
               </h1>
               <p class="text-slate-600 text-lg leading-relaxed max-w-2xl mx-auto">
                  Stream subcarrier perturbations in real-time between <strong>Ali Board (TX)</strong> and <strong>Sabi Board (RX)</strong>. Record labeled datasets and inspect signal metrics with zero CLI friction.
               </p>
            </div>

            <!-- LIVE STUDIO DASHBOARD CONTAINER -->
            <div class="bg-white border-2 border-slate-300 rounded-3xl shadow-xl overflow-hidden p-6 md:p-8 space-y-6">

               <!-- Header strip inside Studio -->
               <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-5 border-b border-slate-200">
                  <div class="flex items-center gap-3">
                     <span class="relative flex h-3 w-3">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                     </span>
                     <div>
                        <h2 class="text-lg font-bold text-slate-900">Live 128-Subcarrier Waterfall Monitor</h2>
                        <p class="text-xs text-slate-500">Channel 11 &middot; HT20 &middot; 60 Hz &middot; Real-Time Wireless Amplitude</p>
                     </div>
                  </div>
                  <div class="flex items-center gap-3 text-xs font-mono">
                     <div class="px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-700">
                        <span class="text-slate-400">Rate:</span> <strong id="live-rate-studio" class="text-blue-600 font-bold">58.8 pkt/s</strong>
                     </div>
                     <div class="px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-700">
                        <span class="text-slate-400">RSSI:</span> <strong id="live-rssi-studio" class="text-emerald-600 font-bold">-45 dBm</strong>
                     </div>
                     <div class="px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-slate-700">
                        <span class="text-slate-400">Seq:</span> <strong id="live-seq-studio" class="text-violet-600 font-bold">#48190</strong>
                     </div>
                  </div>
               </div>

               <!-- Live Subcarrier Canvas -->
               <div class="w-full bg-slate-950 rounded-2xl p-4 border border-slate-800 shadow-inner">
                  <div class="flex items-center justify-between text-xs text-slate-400 mb-2">
                     <span class="font-mono">Subcarrier 0 (DC) &rarr; Subcarrier 127</span>
                     <span>Wave your hand in the room to see the perturbation bars jump</span>
                  </div>
                  <div class="w-full h-48 flex items-end">
                     <canvas id="csi-canvas" class="w-full h-full"></canvas>
                  </div>
               </div>

               <!-- Controls & Action Hub (3 Columns) -->
               <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">

                  <!-- Col 1: Recording & Labeling Controls -->
                  <div class="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4">
                     <div class="flex items-center justify-between">
                        <h3 class="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                           <span>🎬</span> Session Labeling
                        </h3>
                        <span class="text-[11px] text-slate-500 font-mono">Auto CSV save</span>
                     </div>

                     <!-- Label Presets -->
                     <div>
                        <label class="text-xs font-semibold text-slate-600 block mb-1.5">Activity Presets:</label>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                           <button onclick="setLabel('empty_room')" class="px-3 py-2 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 font-medium rounded-xl text-slate-700 border border-slate-200 shadow-xs transition text-left">
                              🏢 Empty Room
                           </button>
                           <button onclick="setLabel('person_sitting')" class="px-3 py-2 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 font-medium rounded-xl text-slate-700 border border-slate-200 shadow-xs transition text-left">
                              🪑 Person Sitting
                           </button>
                           <button onclick="setLabel('person_walking')" class="px-3 py-2 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 font-medium rounded-xl text-slate-700 border border-slate-200 shadow-xs transition text-left">
                              🚶 Walking
                           </button>
                           <button onclick="setLabel('hand_wave')" class="px-3 py-2 bg-white hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 font-medium rounded-xl text-slate-700 border border-slate-200 shadow-xs transition text-left">
                              👋 Hand Gestures
                           </button>
                        </div>
                     </div>

                     <!-- Custom Label Input -->
                     <div>
                        <label class="text-xs font-semibold text-slate-600 block mb-1">Custom Activity Name:</label>
                        <input id="label-input" type="text" value="empty_room" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                     </div>

                     <!-- Duration Select -->
                     <div>
                        <label class="text-xs font-semibold text-slate-600 block mb-1">Capture Duration:</label>
                        <select id="duration-select" class="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-blue-500">
                           <option value="15">15 Seconds (Fast Test)</option>
                           <option value="30">30 Seconds</option>
                           <option value="60" selected>60 Seconds (Official M3 Standard)</option>
                           <option value="120">120 Seconds (Extended)</option>
                           <option value="0">Continuous (Manual Stop)</option>
                        </select>
                     </div>

                     <!-- Big Start / Stop Button -->
                     <button id="record-btn" onclick="toggleRecord()" class="w-full py-3 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-md shadow-blue-500/20 transition-all flex items-center justify-center gap-2 cursor-pointer">
                        <span id="record-icon" class="h-3 w-3 rounded-full bg-white animate-ping"></span>
                        <span id="record-text">Start Recording Session</span>
                     </button>

                     <!-- Live Recording Banner -->
                     <div id="recording-status-box" class="hidden bg-rose-50 border border-rose-200 p-3.5 rounded-xl text-xs space-y-1">
                        <div class="flex items-center justify-between text-rose-800 font-bold">
                           <span class="flex items-center gap-1.5">
                              <span class="h-2 w-2 rounded-full bg-rose-600 animate-ping"></span> Recording in progress
                           </span>
                           <span id="rec-timer" class="font-mono text-sm">0.0s / 60s</span>
                        </div>
                        <p class="text-rose-600 text-[11px]">Writing packets to file &middot; Saved: <strong id="rec-packets" class="font-mono">0</strong></p>
                     </div>
                  </div>

                  <!-- Col 2: Latest Session Analysis -->
                  <div class="bg-slate-50 border border-slate-200 rounded-2xl p-5 flex flex-col justify-between">
                     <div>
                        <div class="flex items-center justify-between mb-3">
                           <h3 class="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                              <span>📊</span> Data Quality Scorecard
                           </h3>
                           <span class="text-xs text-emerald-600 font-semibold bg-emerald-100 border border-emerald-200 px-2 py-0.5 rounded-full">Automatic Gate</span>
                        </div>
                        <p class="text-xs text-slate-500 mb-4">Evaluated against the Milestone 2 & 3 baseline standards.</p>

                        <div id="analysis-container">
                           <!-- Default card -->
                           <div class="grid grid-cols-2 gap-3 mb-4">
                              <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                                 <span class="text-[11px] text-slate-500 block">Baseline Delivery</span>
                                 <strong class="text-lg font-bold text-emerald-600 font-mono">99.8%</strong>
                              </div>
                              <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                                 <span class="text-[11px] text-slate-500 block">Jitter (&sigma;)</span>
                                 <strong class="text-lg font-bold text-blue-600 font-mono">1.29 ms</strong>
                              </div>
                              <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                                 <span class="text-[11px] text-slate-500 block">Sampling Rate</span>
                                 <strong class="text-lg font-bold text-violet-600 font-mono">58.7 pkt/s</strong>
                              </div>
                              <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                                 <span class="text-[11px] text-slate-500 block">Gaps &gt; 3&times; dt</span>
                                 <strong class="text-lg font-bold text-emerald-600 font-mono">0</strong>
                              </div>
                           </div>
                           <p class="text-[11px] text-slate-500 text-center">Official baseline loaded from <code class="text-slate-800">csi_udp_ht20_60hz.csv</code></p>
                        </div>
                     </div>

                     <div class="pt-4 border-t border-slate-200 text-xs text-slate-500 flex items-center justify-between">
                        <span>Total Lifetime Packets:</span>
                        <strong id="total-packets" class="font-mono text-slate-900">0</strong>
                     </div>
                  </div>

                  <!-- Col 3: Hardware Nodes & Link Health -->
                  <div class="bg-slate-50 border border-slate-200 rounded-2xl p-5 space-y-4">
                     <h3 class="text-sm font-bold uppercase tracking-wider text-slate-700 flex items-center gap-2">
                        <span>🛰️</span> Active Nodes & Mesh
                     </h3>

                     <!-- Ali Board -->
                     <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
                        <div class="flex items-center justify-between mb-1.5">
                           <div class="flex items-center gap-2">
                              <span class="text-base">📡</span>
                              <strong class="text-sm font-semibold text-slate-900">Ali Board</strong>
                           </div>
                           <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">Transmitter</span>
                        </div>
                        <p class="text-xs text-slate-500">ESP32 &middot; MAC: <code class="text-slate-700">1a:00:00:00:00:00</code></p>
                        <p class="text-xs text-slate-500">60 pkt/s &middot; Standalone 5V Power &middot; Ch 11</p>
                     </div>

                     <!-- Sabi Board -->
                     <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
                        <div class="flex items-center justify-between mb-1.5">
                           <div class="flex items-center gap-2">
                              <span class="text-base">🛰️</span>
                              <strong class="text-sm font-semibold text-slate-900">Sabi Board</strong>
                           </div>
                           <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-violet-100 text-violet-800">Receiver</span>
                        </div>
                        <p class="text-xs text-slate-500">ESP32 &middot; MAC: <code class="text-slate-700">28:56:2f:49:59:58</code></p>
                        <p class="text-xs text-slate-500">Wi-Fi UDP &rarr; Port 9000 &middot; 128 Subcarriers</p>
                     </div>

                     <!-- Router Info -->
                     <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between text-xs">
                        <div>
                           <span class="font-semibold text-slate-800 block">Project_CSI_Router</span>
                           <span class="text-slate-500">Offline Subnet: 192.168.2.X</span>
                        </div>
                        <span class="px-2 py-1 bg-emerald-50 text-emerald-700 font-semibold rounded-lg border border-emerald-200">Connected</span>
                     </div>
                  </div>

               </div>
            </div>

         </div>
      </section>

      <!-- ─── HARDWARE ARCHITECTURE (BENTO) ─── -->
      <section id="hardware-nodes" class="px-4 md:px-8 py-16">
         <div class="max-w-7xl mx-auto">

            <div class="flex flex-col gap-6 mb-12 md:mb-16 lg:flex-row lg:items-end lg:justify-between">
               <div>
                  <span class="text-xs font-semibold uppercase tracking-widest text-blue-600 block mb-2">Hardware Setup</span>
                  <h2 class="text-3xl font-semibold leading-[1.1] max-w-xl md:text-4xl lg:text-5xl">
                     Portable, Camera-Free Sensing Kit
                  </h2>
               </div>
               <p class="text-slate-600 max-w-md leading-relaxed lg:text-right">
                  Everything runs locally. No cloud latency, no privacy breaches, and zero serial bottlenecks with our wireless UDP pipeline.
               </p>
            </div>

            <!-- Three cards -->
            <div class="grid gap-y-8 md:grid-cols-3 md:divide-x md:divide-slate-300">
               <div class="md:pr-8 lg:pr-12">
                  <p class="text-4xl font-medium tracking-tight text-blue-600">Ali Board</p>
                  <p class="mt-4 font-semibold text-lg">Autonomous RF Transmitter</p>
                  <p class="mt-2 text-sm text-slate-600 leading-relaxed">
                     ESP32-D0WD-V3 running <code class="text-xs bg-slate-100 p-1 rounded font-mono">csi_send</code>. Broadcasts fixed ESP-NOW packets at 60 Hz on Channel 11. Powered by any USB phone charger or powerbank anywhere in the room.
                  </p>
               </div>

               <div class="md:px-8 lg:px-12">
                  <p class="text-4xl font-medium tracking-tight text-violet-600">Sabi Board</p>
                  <p class="mt-4 font-semibold text-lg">Subcarrier CSI Receiver</p>
                  <p class="mt-2 text-sm text-slate-600 leading-relaxed">
                     ESP32-D0WD-V3 capturing 128 complex subcarrier values per packet. Connects to Wi-Fi and streams live UDP data to your laptop on port 9000 at &gt;99.8% delivery.
                  </p>
               </div>

               <div class="md:pl-8 lg:pl-12">
                  <p class="text-4xl font-medium tracking-tight text-emerald-600">TEData Lab</p>
                  <p class="mt-4 font-semibold text-lg">Dedicated Offline Router</p>
                  <p class="mt-2 text-sm text-slate-600 leading-relaxed">
                     <code class="text-xs bg-slate-100 p-1 rounded font-mono">Project_CSI_Router</code> on 2.4 GHz Channel 11 with isolated subnet <code class="text-xs bg-slate-100 p-1 rounded font-mono">192.168.2.X</code>. Zero network congestion and zero interference with your home internet.
                  </p>
               </div>
            </div>
         </div>
      </section>

      <!-- ─── DATA QUALITY BENCHMARKS ─── -->
      <section id="benchmarks" class="py-16 bg-[#08080f] text-white">
         <div class="max-w-7xl mx-auto px-4 md:px-8">

            <div class="max-w-3xl mb-12">
               <span class="text-xs font-semibold uppercase tracking-widest text-blue-400 block mb-2">Milestone Validation</span>
               <h2 class="text-3xl font-semibold leading-[1.1] md:text-4xl lg:text-5xl">
                  Measured, Reproducible Signal Quality
               </h2>
               <p class="text-slate-400 mt-4 leading-relaxed">
                  How we solved the CP2102 serial bottleneck (H-09) and achieved a 99.8% delivery baseline over Wi-Fi UDP.
               </p>
            </div>

            <!-- Bento row 1 -->
            <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
               <div class="bg-white/5 border border-white/10 rounded-2xl p-6 lg:col-span-3">
                  <div class="flex items-start justify-between mb-6">
                     <div>
                        <h3 class="text-base font-semibold text-white">Transport Delivery Comparison</h3>
                        <p class="text-sm text-slate-400">Evolution across project milestones</p>
                     </div>
                     <span class="text-xs font-bold text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 rounded-full px-3 py-1">99.8% Peak</span>
                  </div>

                  <div class="space-y-4">
                     <div>
                        <div class="flex justify-between text-xs text-slate-300 mb-1">
                           <span>Run 1: Serial HT40 @ 100 pkt/s (UART Saturated)</span>
                           <span class="text-rose-400 font-bold">76.9% (1,264 dropped)</span>
                        </div>
                        <div class="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                           <div class="h-full bg-rose-500 rounded-full" style="width: 76.9%"></div>
                        </div>
                     </div>

                     <div>
                        <div class="flex justify-between text-xs text-slate-300 mb-1">
                           <span>Run 2: Serial HT20 @ 60 pkt/s (M2 Baseline)</span>
                           <span class="text-amber-400 font-bold">99.4% (22 dropped)</span>
                        </div>
                        <div class="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                           <div class="h-full bg-amber-400 rounded-full" style="width: 99.4%"></div>
                        </div>
                     </div>

                     <div>
                        <div class="flex justify-between text-xs text-slate-300 mb-1">
                           <span>M3-P1: Wi-Fi UDP HT20 @ 60 pkt/s (Current Champion)</span>
                           <span class="text-emerald-400 font-bold">99.8% (Only 7 dropped out of 3,530)</span>
                        </div>
                        <div class="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                           <div class="h-full bg-emerald-400 rounded-full shadow-lg shadow-emerald-400/30" style="width: 99.8%"></div>
                        </div>
                     </div>
                  </div>
               </div>

               <!-- Stat Card -->
               <div class="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
                  <p class="text-sm text-slate-400 font-semibold uppercase tracking-wider">Interval Jitter (&sigma;)</p>
                  <div>
                     <p class="text-5xl font-medium leading-none mb-2 text-white">1.29<span class="text-2xl text-slate-400 font-normal ml-1">ms</span></p>
                     <p class="text-xs text-slate-400 leading-relaxed">Median inter-packet time: 17.0 ms (rock-solid 60 Hz sampling)</p>
                  </div>
                  <div class="pt-3 border-t border-white/10 text-xs text-emerald-400 font-semibold">
                     &check; 0 Gaps &gt; 3&times; dt
                  </div>
               </div>
            </div>

            <!-- Bento row 2 -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
               <div class="bg-white/5 border border-white/10 rounded-2xl p-6">
                  <span class="text-xs font-semibold text-blue-400 uppercase tracking-widest block mb-2">Payload Structure</span>
                  <p class="text-2xl font-bold text-white mb-2">128 Subcarriers</p>
                  <p class="text-xs text-slate-400 leading-relaxed">256 raw signed int8 samples (64 complex I/Q subcarrier pairs). Preserved without downsampling.</p>
               </div>
               <div class="bg-white/5 border border-white/10 rounded-2xl p-6">
                  <span class="text-xs font-semibold text-violet-400 uppercase tracking-widest block mb-2">First Word Correction</span>
                  <p class="text-2xl font-bold text-white mb-2">first_word_invalid</p>
                  <p class="text-xs text-slate-400 leading-relaxed">Hardware flags first CSI word as invalid on 100% of packets; stripped during preprocessing to avoid constant artifact.</p>
               </div>
               <div class="bg-white/5 border border-white/10 rounded-2xl p-6">
                  <span class="text-xs font-semibold text-emerald-400 uppercase tracking-widest block mb-2">Power Integrity</span>
                  <p class="text-2xl font-bold text-white mb-2">-45.3 dBm</p>
                  <p class="text-xs text-slate-400 leading-relaxed">Average RSSI with &plusmn;1.47 dBm stability and -97 dBm noise floor on Channel 11.</p>
               </div>
            </div>

         </div>
      </section>

      <!-- ─── DATASETS TABLE ─── -->
      <section id="datasets" class="px-4 md:px-8 py-16 bg-white">
         <div class="max-w-6xl mx-auto">
            
            <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
               <div>
                  <span class="text-xs font-semibold uppercase tracking-widest text-blue-600 block mb-1">Dataset Archive</span>
                  <h2 class="text-3xl font-semibold text-slate-900">Recorded CSI Sessions (<code class="text-lg font-mono">data/</code>)</h2>
               </div>
               <button onclick="refreshFiles()" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-xl border border-slate-300 transition flex items-center gap-1.5 cursor-pointer">
                  <span>🔄</span> Refresh File List
               </button>
            </div>

            <div class="border border-slate-300 rounded-2xl overflow-hidden shadow-xs">
               <div class="overflow-x-auto">
                  <table class="w-full text-left text-xs">
                     <thead class="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                        <tr>
                           <th class="py-3 px-4">Filename</th>
                           <th class="py-3 px-4">File Size</th>
                           <th class="py-3 px-4">Date Recorded</th>
                           <th class="py-3 px-4 text-right">Actions</th>
                        </tr>
                     </thead>
                     <tbody id="files-table-body" class="divide-y divide-slate-200 font-mono">
                        <tr>
                           <td colspan="4" class="p-6 text-center text-slate-400 font-sans">Loading saved dataset files...</td>
                        </tr>
                     </tbody>
                  </table>
               </div>
            </div>

         </div>
      </section>

      <!-- ─── FAQ ─── -->
      <section id="faq" class="px-4 md:px-8 py-16 bg-slate-50 border-t border-slate-200">
         <div class="max-w-4xl mx-auto">
            <div class="text-center mb-12">
               <span class="text-xs font-semibold uppercase tracking-widest text-blue-600 block mb-2">Knowledge Base</span>
               <h2 class="text-3xl font-semibold leading-[1.1] md:text-4xl text-slate-900">Frequently Asked Questions</h2>
            </div>

            <div class="space-y-4">

               <div class="faq-item border border-slate-300 rounded-xl" data-open="false">
                  <button class="faq-btn cursor-pointer w-full rounded-xl flex items-center justify-between gap-4 px-6 py-5 text-left font-medium bg-white hover:bg-gray-50 transition-colors focus:outline-none">
                     Do Ali Board and Sabi Board need to be plugged into the laptop?
                     <svg class="faq-chevron size-4 text-slate-400 transition-transform" viewBox="0 0 12 12" fill="none">
                        <path d="M2.5 4.5L6 8l3.5-3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
                     </svg>
                  </button>
                  <div class="faq-body grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 ease-in-out">
                     <div class="overflow-hidden">
                        <div class="px-6 pb-6 pt-4 border-t border-slate-200 text-slate-600 leading-relaxed text-sm">
                           <strong>No!</strong> Neither board needs a serial connection for data logging anymore. Ali Board (Transmitter) only requires 5V power from any phone charger or powerbank anywhere in the room. Sabi Board (Receiver) connects to the TEData router over Wi-Fi and streams all packets via UDP directly to your PC.
                        </div>
                     </div>
                  </div>
               </div>

               <div class="faq-item border border-slate-300 rounded-xl" data-open="false">
                  <button class="faq-btn cursor-pointer w-full rounded-xl flex items-center justify-between gap-4 px-6 py-5 text-left font-medium bg-white hover:bg-gray-50 transition-colors focus:outline-none">
                     Does the TEData router require an internet or DSL connection?
                     <svg class="faq-chevron size-4 text-slate-400 transition-transform" viewBox="0 0 12 12" fill="none">
                        <path d="M2.5 4.5L6 8l3.5-3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
                     </svg>
                  </button>
                  <div class="faq-body grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 ease-in-out">
                     <div class="overflow-hidden">
                        <div class="px-6 pb-6 pt-4 border-t border-slate-200 text-slate-600 leading-relaxed text-sm">
                           <strong>No internet required at all.</strong> The system operates 100% on a local subnet (<code class="bg-slate-100 px-1 py-0.5 rounded text-xs">192.168.2.X</code>). The router simply acts as an isolated local switch. Your PC maintains full internet access through its normal Wi-Fi simultaneously.
                        </div>
                     </div>
                  </div>
               </div>

               <div class="faq-item border border-slate-300 rounded-xl" data-open="false">
                  <button class="faq-btn cursor-pointer w-full rounded-xl flex items-center justify-between gap-4 px-6 py-5 text-left font-medium bg-white hover:bg-gray-50 transition-colors focus:outline-none">
                     What are the 128 subcarriers shown in the live graph?
                     <svg class="faq-chevron size-4 text-slate-400 transition-transform" viewBox="0 0 12 12" fill="none">
                        <path d="M2.5 4.5L6 8l3.5-3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
                     </svg>
                  </button>
                  <div class="faq-body grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 ease-in-out">
                     <div class="overflow-hidden">
                        <div class="px-6 pb-6 pt-4 border-t border-slate-200 text-slate-600 leading-relaxed text-sm">
                           In OFDM Wi-Fi, radio signals are split across multiple frequency subcarriers. As physical bodies move through the space, they absorb, scatter, and reflect signals along multipath propagation routes. This causes frequency-selective fading that shows up as distinct perturbation patterns across the subcarrier bars.
                        </div>
                     </div>
                  </div>
               </div>

               <div class="faq-item border border-slate-300 rounded-xl" data-open="false">
                  <button class="faq-btn cursor-pointer w-full rounded-xl flex items-center justify-between gap-4 px-6 py-5 text-left font-medium bg-white hover:bg-gray-50 transition-colors focus:outline-none">
                     How will AI use this data for activity recognition?
                     <svg class="faq-chevron size-4 text-slate-400 transition-transform" viewBox="0 0 12 12" fill="none">
                        <path d="M2.5 4.5L6 8l3.5-3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path>
                     </svg>
                  </button>
                  <div class="faq-body grid grid-rows-[0fr] transition-[grid-template-rows] duration-300 ease-in-out">
                     <div class="overflow-hidden">
                        <div class="px-6 pb-6 pt-4 border-t border-slate-200 text-slate-600 leading-relaxed text-sm">
                           Each CSV recording represents a temporal spectrogram of amplitude and phase variations. Using CNNs, LSTMs, or 1D-temporal transformers, models learn the distinctive spatial-temporal signatures of actions (e.g. empty room = stationary noise floor; walking = large rhythmic Doppler shifts; gestures = sharp localized frequency deviations).
                        </div>
                     </div>
                  </div>
               </div>

            </div>
         </div>
      </section>

   </main>

   <!-- ─── FOOTER ─── -->
   <footer class="bg-[#08080f] px-4 md:px-8 py-12 text-slate-400 border-t border-white/10 text-xs">
      <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
         <div class="flex items-center gap-3">
            <div class="w-7 h-7 rounded-lg flex items-center justify-center bg-gradient-to-br from-blue-600 to-violet-600">
               <svg class="w-3.5 h-3.5 text-white" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r="3" fill="white" />
               </svg>
            </div>
            <div>
               <strong class="text-white text-sm block">Wi-Fi CSI Human Sensing Hub</strong>
               <span class="text-slate-500">Graduation Project &middot; ESP-IDF v5.4.4 &middot; Milestone 3</span>
            </div>
         </div>

         <div class="flex items-center gap-6">
            <div class="flex items-center gap-2">
               <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
               <span>UDP Listener: Port 9000 Online</span>
            </div>
            <span>&middot;</span>
            <div class="flex items-center gap-2">
               <span class="w-2 h-2 rounded-full bg-blue-500"></span>
               <span>HTTP Dashboard: Port 8080</span>
            </div>
         </div>

         <p class="text-slate-600">&copy; 2026 Ali & Team. All project rights reserved.</p>
      </div>
   </footer>

   <!-- ─── SCRIPT LOGIC ─── -->
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
         const maxAmp = 65.0; // scale factor

         for (let i = 0; i < amps.length; i++) {
            const amp = amps[i];
            const barHeight = Math.min(h, (amp / maxAmp) * h);
            const x = i * barWidth;
            const y = h - barHeight;

            // Electric blue to cyan gradient
            const hue = 190 + (i / amps.length) * 50;
            ctx.fillStyle = `hsl(${hue}, 95%, 55%)`;
            ctx.fillRect(x, y, Math.max(1, barWidth - 1), barHeight);
         }
      }

      function renderAnalysis(data) {
         if (!data || data.error) return;
         const html = `
            <div class="grid grid-cols-2 gap-3 mb-3">
               <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                  <span class="text-[11px] text-slate-500 block">Session Delivery</span>
                  <strong class="text-lg font-bold ${data.delivery_pct >= 98 ? 'text-emerald-600' : 'text-amber-600'} font-mono">${data.delivery_pct}%</strong>
               </div>
               <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                  <span class="text-[11px] text-slate-500 block">Session Jitter (&sigma;)</span>
                  <strong class="text-lg font-bold text-blue-600 font-mono">${data.jitter_ms} ms</strong>
               </div>
               <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                  <span class="text-[11px] text-slate-500 block">Actual Rate</span>
                  <strong class="text-lg font-bold text-violet-600 font-mono">${data.rate} pkt/s</strong>
               </div>
               <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-xs text-center">
                  <span class="text-[11px] text-slate-500 block">Packets Saved</span>
                  <strong class="text-lg font-bold text-slate-900 font-mono">${data.packets}</strong>
               </div>
            </div>
            <div class="p-2.5 rounded-xl bg-blue-50 border border-blue-200 text-[11px] text-blue-900 font-mono flex items-center justify-between">
               <span class="truncate max-w-xs font-semibold">${data.file}</span>
               <span class="text-blue-700">Duration: ${data.duration}s</span>
            </div>
         `;
         document.getElementById('analysis-container').innerHTML = html;
      }

      async function analyzeFile(fname) {
         document.getElementById('analysis-container').innerHTML = `
            <div class="py-8 text-center text-xs text-blue-600 font-semibold animate-pulse">
               Analyzing ${fname}... Please wait.
            </div>
         `;
         const res = await fetch(`/api/analyze?file=${encodeURIComponent(fname)}`);
         const data = await res.json();
         renderAnalysis(data);
         window.location.hash = '#live-studio';
      }

      async function refreshFiles() {
         const res = await fetch('/api/files');
         const files = await res.json();
         const tbody = document.getElementById('files-table-body');
         if (files.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="p-6 text-center text-slate-500">No files found.</td></tr>';
            return;
         }
         tbody.innerHTML = files.map(f => `
            <tr class="hover:bg-slate-50 transition">
               <td class="py-3 px-4 text-slate-900 font-semibold truncate max-w-xs">${f.name}</td>
               <td class="py-3 px-4 text-slate-500">${f.size_kb} KB</td>
               <td class="py-3 px-4 text-slate-500">${f.date}</td>
               <td class="py-3 px-4 text-right font-sans">
                  <button onclick="analyzeFile('${f.name}')" class="px-3 py-1 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 font-semibold transition cursor-pointer">
                     Inspect Scorecard
                  </button>
               </td>
            </tr>
         `).join('');
      }

      async function pollStatus() {
         try {
            const res = await fetch('/api/status');
            const data = await res.json();

            // Header & Studio metrics
            document.getElementById('nav-rate').innerText = `${data.current_rate} pkt/s`;
            document.getElementById('live-rate-studio').innerText = `${data.current_rate} pkt/s`;
            document.getElementById('live-rssi-studio').innerText = `${data.rssi} dBm`;
            document.getElementById('live-seq-studio').innerText = `#${data.seq}`;
            document.getElementById('total-packets').innerText = data.packet_counter.toLocaleString();

            // Draw subcarrier canvas
            if (data.subcarriers && data.subcarriers.length > 0) {
               renderSubcarriers(data.subcarriers);
            }

            // Recording UI status
            isRecording = data.is_recording;
            const btn = document.getElementById('record-btn');
            const text = document.getElementById('record-text');
            const icon = document.getElementById('record-icon');
            const statusBox = document.getElementById('recording-status-box');

            if (isRecording) {
               btn.className = "w-full py-3 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-700 hover:to-red-700 text-white shadow-lg shadow-rose-500/30 transition-all flex items-center justify-center gap-2 cursor-pointer";
               text.innerText = "Stop Recording";
               icon.className = "h-3 w-3 rounded-full bg-white animate-pulse";
               statusBox.classList.remove('hidden');
               document.getElementById('rec-timer').innerText = `${data.record_elapsed}s / ${data.record_duration}s`;
               document.getElementById('rec-packets').innerText = data.record_packets;
            } else {
               btn.className = "w-full py-3 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-md shadow-blue-500/20 transition-all flex items-center justify-center gap-2 cursor-pointer";
               text.innerText = "Start Recording Session";
               icon.className = "h-3 w-3 rounded-full bg-white animate-ping";
               statusBox.classList.add('hidden');
            }

            if (data.last_analysis) {
               renderAnalysis(data.last_analysis);
            }
         } catch (e) {
            console.error(e);
         }
      }

      // Mobile Menu & FAQ handlers
      document.addEventListener('DOMContentLoaded', () => {
         const toggleOpen = document.getElementById("toggleOpen");
         const toggleClose = document.getElementById("toggleClose");
         const menu = document.getElementById("collapseMenu");

         toggleOpen.addEventListener("click", () => menu.classList.remove("hidden"));
         toggleClose.addEventListener("click", () => menu.classList.add("hidden"));

         // FAQ Accordion
         document.querySelectorAll('.faq-item').forEach(function (item) {
            item.querySelector('.faq-btn').addEventListener('click', function () {
               var isOpen = item.dataset.open === 'true';
               if (isOpen) {
                  item.dataset.open = 'false';
                  item.querySelector('.faq-body').style.gridTemplateRows = '0fr';
                  item.querySelector('.faq-chevron').style.transform = 'rotate(0deg)';
               } else {
                  item.dataset.open = 'true';
                  item.querySelector('.faq-body').style.gridTemplateRows = '1fr';
                  item.querySelector('.faq-chevron').style.transform = 'rotate(180deg)';
               }
            });
         });

         refreshFiles();
         setInterval(pollStatus, 200);
      });
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
