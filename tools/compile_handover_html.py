import base64
import os

docs_dir = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\docs"
raw_png = os.path.join(docs_dir, "30s_raw_comparison.png")
clean_png = os.path.join(docs_dir, "30s_cleaned_comparison.png")
stages_png = os.path.join(docs_dir, "signal_cleaning_stages.png")

with open(raw_png, "rb") as f:
    b64_raw = base64.b64encode(f.read()).decode("utf-8")

with open(clean_png, "rb") as f:
    b64_clean = base64.b64encode(f.read()).decode("utf-8")

b64_stages = ""
if os.path.exists(stages_png):
    with open(stages_png, "rb") as f:
        b64_stages = base64.b64encode(f.read()).decode("utf-8")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Role 2 Technical Handover Report: Wi-Fi CSI Signal Processing & Feature Engineering</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --primary-light: #eff6ff;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --border: #e2e8f0;
            --accent-green: #059669;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.65;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1040px;
            margin: 0 auto;
            background: var(--card-bg);
            padding: 50px 60px;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.06);
            border: 1px solid var(--border);
        }}
        .header-badge {{
            display: inline-block;
            background: #dcfce7;
            color: var(--accent-green);
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        h1 {{
            font-size: 30px;
            font-weight: 800;
            color: var(--text-main);
            margin: 0 0 16px 0;
            line-height: 1.25;
            border-bottom: 2px solid var(--border);
            padding-bottom: 20px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            background: #f8fafc;
            padding: 18px 24px;
            border-radius: 10px;
            margin-bottom: 36px;
            border: 1px solid var(--border);
            font-size: 14px;
        }}
        .meta-item strong {{
            display: block;
            color: var(--text-muted);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        h2 {{
            font-size: 21px;
            font-weight: 700;
            color: #1e293b;
            margin-top: 42px;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 700;
            color: #334155;
            margin-top: 24px;
            margin-bottom: 10px;
        }}
        p, li {{
            color: var(--text-muted);
            font-size: 15px;
        }}
        code {{
            background: #f1f5f9;
            color: #d946ef;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13.5px;
        }}
        pre {{
            background: #0f172a;
            color: #f8fafc;
            padding: 18px 22px;
            border-radius: 10px;
            overflow-x: auto;
            font-size: 13.5px;
            line-height: 1.5;
        }}
        pre code {{
            background: transparent;
            color: inherit;
            padding: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 24px 0;
            font-size: 14px;
        }}
        th, td {{
            text-align: left;
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: #f1f5f9;
            color: var(--text-main);
            font-weight: 700;
        }}
        tr:hover td {{
            background-color: #f8fafc;
        }}
        .figure-card {{
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            margin: 28px 0;
            box-shadow: 0 2px 12px rgba(0,0,0,0.03);
        }}
        .figure-card img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .figure-caption {{
            padding: 12px 18px;
            font-size: 13px;
            color: var(--text-muted);
            background: #f8fafc;
            border-top: 1px solid var(--border);
            font-weight: 500;
        }}
        .stage-box {{
            background: #f8fafc;
            border-left: 4px solid var(--primary);
            padding: 16px 20px;
            margin-bottom: 16px;
            border-radius: 0 8px 8px 0;
        }}
        .stage-title {{
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 4px;
            font-size: 15px;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin: 24px 0;
        }}
        .stat-card {{
            background: var(--primary-light);
            border: 1px solid #bfdbfe;
            border-radius: 10px;
            padding: 18px;
            text-align: center;
        }}
        .stat-num {{
            font-size: 26px;
            font-weight: 800;
            color: var(--primary);
            margin-bottom: 4px;
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; border: none; padding: 0; max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <span class="header-badge">Role 2 Official Handover</span>
        <h1>Wi-Fi CSI Signal Processing & Feature Engineering</h1>
        
        <div class="meta-grid">
            <div class="meta-item">
                <strong>Author / Role</strong>
                Mohammed Sabry (Role 2 Lead)
            </div>
            <div class="meta-item">
                <strong>Recipient Team</strong>
                Project Supervisor & ML Team (Role 3)
            </div>
            <div class="meta-item">
                <strong>Deliverable Status</strong>
                Completed & Verified (100%)
            </div>
            <div class="meta-item">
                <strong>Master Dataset</strong>
                <code>data/extracted_features.csv</code>
            </div>
        </div>

        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-num">58.7</div>
                <div class="stat-label">Packet Rate (Hz)</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">116</div>
                <div class="stat-label">Active Subcarriers</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">656</div>
                <div class="stat-label">Extracted Windows</div>
            </div>
            <div class="stat-card">
                <div class="stat-num">22</div>
                <div class="stat-label">Features / Window</div>
            </div>
        </div>

        <h2>1. Executive Summary & Role Mandate</h2>
        <p>As <strong>Role 2 (Signal Processing & Feature Engineering)</strong>, my mandate is to bridge the physical ESP32 Wi-Fi hardware measurements with the Machine Learning classifier (Role 3). Raw Channel State Information (CSI) packets are corrupted by static multipath bias from walls, high-frequency electromagnetic noise, receiver AGC gain shifts, and unmodulated OFDM tones.</p>
        
        <p>This report documents the completed deliverables:</p>
        <ul>
            <li><strong>6-Stage Signal Cleaning Pipeline (<code>tools/clean_csi_pipeline.py</code>):</strong> Transforms noisy raw CSI matrices into clean, zero-centered, human-motion-isolated waveforms.</li>
            <li><strong>Empirical Validation Proof (<code>tools/plot_30s_validation.py</code>):</strong> Rigorous side-by-side verification between 1-minute Empty Room and Walking sessions.</li>
            <li><strong>Feature Extraction Engine (<code>tools/extract_features.py</code>):</strong> Automatic sliding-window feature extractor generating 22 time-domain, Doppler frequency, and spatial cross-channel features.</li>
            <li><strong>Master Handover Dataset (<code>data/extracted_features.csv</code>):</strong> 656 fully labeled, standardized feature vectors with zero missing values across 4 activity classes.</li>
        </ul>

        <h2>2. Physical Hardware & Sensing Parameters</h2>
        <table>
            <thead>
                <tr>
                    <th>Parameter</th>
                    <th>Specification</th>
                    <th>Role in Sensing System</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Transmitter (TX Node)</strong></td>
                    <td>ESP32-WROOM-32 (Ali Board)</td>
                    <td>Broadcasts beacon frames at 60 Hz on Wi-Fi Channel 11 (2.462 GHz).</td>
                </tr>
                <tr>
                    <td><strong>Receiver (RX Node)</strong></td>
                    <td>ESP32-WROOM-32 (Sabi Board)</td>
                    <td>Station client attached to dedicated router; streams CSI via UDP port 9000.</td>
                </tr>
                <tr>
                    <td><strong>Sampling Rate (f<sub>s</sub>)</strong></td>
                    <td><strong>58.7 packets/sec</strong></td>
                    <td>17.03 ms interval; satisfies Nyquist requirement for human Doppler (&le; 10 Hz).</td>
                </tr>
                <tr>
                    <td><strong>OFDM Modulation</strong></td>
                    <td>802.11n HT20</td>
                    <td>128 subcarriers total: 116 active communication tones, 12 guard/null tones dropped.</td>
                </tr>
                <tr>
                    <td><strong>Delivery Reliability</strong></td>
                    <td><strong>&gt; 98.2%</strong></td>
                    <td>Packet sequence continuity verified over &gt; 100,000 packets.</td>
                </tr>
            </tbody>
        </table>

        <h2>3. The 6-Stage DSP Cleaning Pipeline</h2>
        <p>Indoor Wi-Fi signals decompose into static reflection and dynamic human multipath: <code>H(f, t) = H_static + H_dynamic(t)</code>. The 6-stage pipeline strips <code>H_static</code> and isolates <code>H_dynamic(t)</code>:</p>

        <div class="stage-box">
            <div class="stage-title">Stage 1: Complex Demodulation &amp; Subcarrier 0 Drop</div>
            <div>Decodes signed IQ bytes to magnitude <code>A = sqrt(I&sup2; + Q&sup2;)</code> and removes subcarrier 0 to discard AGC settling transients and local oscillator carrier feedthrough.</div>
        </div>
        <div class="stage-box">
            <div class="stage-title">Stage 2: Dead Guard &amp; DC Null Masking</div>
            <div>Scans mean subcarrier energy and masks 11 unmodulated tones (channels [27..35, 94, 96]), leaving 116 active communication tones without division-by-zero risk.</div>
        </div>
        <div class="stage-box">
            <div class="stage-title">Stage 3: Fast Vectorized Hampel Despiking</div>
            <div>Evaluates rolling Median Absolute Deviation (MAD, window=7) to replace transmission impulse bursts and packet corruption spikes with local medians (&lt; 0.2s runtime).</div>
        </div>
        <div class="stage-box">
            <div class="stage-title">Stage 4: Zero-Phase Butterworth Bandpass Filter (0.2 Hz &ndash; 10.0 Hz)</div>
            <div>4th-order bidirectional digital filter (<code>filtfilt</code>) that eliminates 0 Hz static DC reflections from stationary walls and cuts out high-frequency noise &gt; 10 Hz, isolating human limb/torso Doppler frequencies.</div>
        </div>
        <div class="stage-box">
            <div class="stage-title">Stage 5: Multi-Subcarrier Spatial PCA Motion Fusion</div>
            <div>Computes Singular Value Decomposition (SVD) across all 116 active subcarriers to project coherent multi-channel motion energy into the dominant PC1 motion profile (&gt; 55% variance explained).</div>
        </div>"""

if b64_stages:
    html += f"""
        <div class="figure-card">
            <img src="data:image/png;base64,{b64_stages}" alt="DSP Cleaning Stages">
            <div class="figure-caption">Figure 1: Visual trace through the progressive DSP cleaning stages.</div>
        </div>"""

html += f"""
        <h2>4. Empirical Validation: Raw vs. Cleaned Data</h2>
        <p>A rigorous test was conducted comparing a 1-minute <strong>Empty Room</strong> recording against a 1-minute <strong>Person Walking</strong> session.</p>

        <h3>4.1 Raw CSI Signals (Before Filtering)</h3>
        <div class="figure-card">
            <img src="data:image/png;base64,{b64_raw}" alt="Raw CSI Comparison">
            <div class="figure-caption">Figure 2: Raw CSI Carrier Amplitude for Empty Room (top) vs. Person Walking (bottom).</div>
        </div>
        <ul>
            <li><strong>Static DC Offset:</strong> Both signals sit atop a huge DC offset (~40 ADC units) caused by static Line-of-Sight propagation.</li>
            <li><strong>Thermal Fuzz:</strong> Empty room exhibits high-frequency electronic jitter (&plusmn;1&ndash;2 ADC units) without periodic structure.</li>
            <li><strong>Multipath Modulation:</strong> Walking creates constructive/destructive wave oscillations (&Delta; ~10&ndash;15 ADC units) and an RSSI shift (-74.5 dBm to -71.1 dBm).</li>
        </ul>

        <h3>4.2 Final Cleaned Signals (After 6-Stage Pipeline)</h3>
        <div class="figure-card">
            <img src="data:image/png;base64,{b64_clean}" alt="Cleaned CSI Comparison">
            <div class="figure-caption">Figure 3: Cleaned CSI Motion Profile (PC1) for Empty Room (top) vs. Person Walking (bottom).</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Performance Metric</th>
                    <th>🏢 Empty Room</th>
                    <th>🚶 Person Walking</th>
                    <th>Physical / DSP Explanation</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Baseline Center</strong></td>
                    <td><strong>0.00</strong></td>
                    <td><strong>0.00</strong></td>
                    <td>Static DC wall carrier removed by 0.2 Hz high-pass filter.</td>
                </tr>
                <tr>
                    <td><strong>Motion Energy (&sigma;)</strong></td>
                    <td><strong>8.62</strong></td>
                    <td><strong>11.45</strong></td>
                    <td>Substantial Doppler variance amplification during walking.</td>
                </tr>
                <tr>
                    <td><strong>Peak-to-Peak Amplitude</strong></td>
                    <td>Quiet baseline</td>
                    <td><strong>74.50 (Coherent)</strong></td>
                    <td>Walking produces large, periodic multipath phase crests.</td>
                </tr>
                <tr>
                    <td><strong>Waveform Morphology</strong></td>
                    <td>Gaussian thermal noise</td>
                    <td>Periodic Doppler gait cadence</td>
                    <td>Clear footstep cycles occurring at 1.2&ndash;2.5 Hz.</td>
                </tr>
            </tbody>
        </table>

        <h2>5. Feature Engineering Engine (<code>tools/extract_features.py</code>)</h2>
        <p>The continuous cleaned waveforms are partitioned into <strong>1.5-second sliding windows</strong> (90 packets) with a <strong>0.5-second step</strong> (66% overlap) to generate 22 features per window:</p>

        <table>
            <thead>
                <tr>
                    <th>Feature Domain</th>
                    <th>Feature Keys</th>
                    <th>Physical Sensing Significance</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>Time-Domain (PC1)</strong></td>
                    <td><code>pc1_var</code>, <code>pc1_std</code>, <code>pc1_mad</code>, <code>pc1_iqr</code>, <code>pc1_ptp</code>, <code>pc1_skew</code>, <code>pc1_kurt</code>, <code>pc1_rms</code>, <code>pc1_zcr</code></td>
                    <td>Measures kinetic motion energy, amplitude spread, asymmetry, impulsiveness, and baseline oscillation frequency.</td>
                </tr>
                <tr>
                    <td><strong>Time-Domain (PC2)</strong></td>
                    <td><code>pc2_var</code>, <code>pc2_std</code>, <code>pc2_mad</code>, <code>pc2_ptp</code></td>
                    <td>Captures orthogonal secondary body dynamics (e.g. arm swing vs. torso translation).</td>
                </tr>
                <tr>
                    <td><strong>Frequency-Domain Doppler</strong></td>
                    <td><code>dominant_freq</code>, <code>energy_low</code>, <code>energy_mid</code>, <code>energy_high</code>, <code>spectral_entropy</code></td>
                    <td>Extracts gait cadence frequency (~1.8 Hz for walking), energy in 0.2-1.5 Hz (torso/breathing), 1.5-4 Hz (footsteps), and spectral entropy.</td>
                </tr>
                <tr>
                    <td><strong>Spatial Cross-Carrier</strong></td>
                    <td><code>sub_var_mean</code>, <code>sub_var_std</code></td>
                    <td>Evaluates variance dispersion across all 116 subcarriers (frequency selectivity of multipath).</td>
                </tr>
                <tr>
                    <td><strong>Signal Power Dynamics</strong></td>
                    <td><code>rssi_mean</code>, <code>rssi_std</code></td>
                    <td>Tracks mean power level and signal volatility.</td>
                </tr>
            </tbody>
        </table>

        <h2>6. Handover to Role 3 (Machine Learning Classifier)</h2>
        <p>The feature extraction pipeline processed all valid recorded sessions into a single consolidated master dataset:</p>

        <div class="meta-grid">
            <div class="meta-item">
                <strong>Dataset Path</strong>
                <code>data/extracted_features.csv</code>
            </div>
            <div class="meta-item">
                <strong>Total Observations</strong>
                656 sliding-window samples
            </div>
            <div class="meta-item">
                <strong>Feature Dimensions</strong>
                22 numerical features
            </div>
            <div class="meta-item">
                <strong>Data Quality</strong>
                0 Missing / NaN values
            </div>
        </div>

        <h3>Class Balance Breakdown:</h3>
        <ul>
            <li>🚶 <strong><code>walking</code>:</strong> 265 samples (40.4%)</li>
            <li>🏢 <strong><code>empty_room</code>:</strong> 215 samples (32.8%)</li>
            <li>🪑 <strong><code>sitting</code>:</strong> 120 samples (18.3%)</li>
            <li>👋 <strong><code>hand_wave</code>:</strong> 56 samples (8.5%)</li>
        </ul>

        <h3>Python Quickstart Code for Role 3:</h3>
        <pre><code>import pandas as pd
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier

# 1. Load the Role 2 Feature Dataset
df = pd.read_csv("data/extracted_features.csv")

# 2. Extract features (X) and ground-truth labels (y)
X = df.drop(columns=["label", "source_file", "win_start_t", "win_end_t"])
y = df["label"]

# 3. Train a Random Forest Classifier with 5-Fold Stratified Cross Validation
clf = RandomForestClassifier(n_estimators=100, random_state=42)
scores = cross_val_score(clf, X, y, cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42))

print(f"5-Fold CV Accuracy: {{scores.mean()*100:.2f}}% (+/- {{scores.std()*100:.2f}}%)")</code></pre>

        <h2>7. Summary of Deliverable Files Handed Over</h2>
        <table>
            <thead>
                <tr>
                    <th>Deliverable Name</th>
                    <th>File Location</th>
                    <th>Purpose / Content</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>DSP Cleaning Pipeline</strong></td>
                    <td><code>tools/clean_csi_pipeline.py</code></td>
                    <td>Reusable 6-stage filtering library for batch or live CSI.</td>
                </tr>
                <tr>
                    <td><strong>Feature Extraction Engine</strong></td>
                    <td><code>tools/extract_features.py</code></td>
                    <td>Batch sliding-window 22-feature generator.</td>
                </tr>
                <tr>
                    <td><strong>Master ML Feature Dataset</strong></td>
                    <td><code>data/extracted_features.csv</code></td>
                    <td>656 samples ready for Role 3 model training.</td>
                </tr>
                <tr>
                    <td><strong>Validation Suite &amp; Figures</strong></td>
                    <td><code>tools/plot_30s_validation.py</code></td>
                    <td>Generates high-resolution validation comparison figures.</td>
                </tr>
                <tr>
                    <td><strong>Stand-Alone HTML Report</strong></td>
                    <td><code>docs/role2_handover_report.html</code></td>
                    <td>Single-file printable documentation with embedded graphs.</td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>"""

out_html = os.path.join(docs_dir, "role2_handover_report.html")
with open(out_html, "w", encoding="utf-8") as f:
    f.write(html)

print(f"[+] Standalone Handover HTML successfully compiled: {out_html}")
