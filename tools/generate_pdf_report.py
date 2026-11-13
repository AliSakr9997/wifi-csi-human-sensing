import os
import warnings
from fpdf import FPDF
from fpdf.enums import XPos, YPos

warnings.filterwarnings("ignore", category=DeprecationWarning)

class Role2PDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 18, 15)
        
    def header(self):
        self.set_font("helvetica", "B", 8)
        self.set_text_color(100, 116, 139)
        self.cell(130, 6, "Wi-Fi CSI Human Sensing Project  |  Role 2 Technical Handover Report", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(50, 6, "Mohammed Sabry", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-14)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(2)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(140, 6, "Senior Graduation Project: Ambient AI Sensing Without Cameras", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(40, 6, f"Page {self.page_no()}", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def chapter_title(self, title):
        self.set_font("helvetica", "B", 13)
        self.set_text_color(30, 58, 138)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(191, 219, 254)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def section_title(self, title):
        self.set_font("helvetica", "B", 10.5)
        self.set_text_color(15, 23, 42)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def body_p(self, text):
        self.set_font("helvetica", "", 9.2)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet(self, bold_prefix, text):
        self.set_font("helvetica", "B", 9)
        self.set_text_color(30, 58, 138)
        self.cell(4, 5, chr(149), new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("helvetica", "B", 9)
        self.set_text_color(15, 23, 42)
        prefix_w = self.get_string_width(bold_prefix) + 1
        self.cell(prefix_w, 5, bold_prefix, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_font("helvetica", "", 9)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 5, text)
        self.ln(1.5)

DOCS_DIR = r"C:\Users\MOHAMMED SABRY\Desktop\wifi_sense_project\wifi-csi-human-sensing\docs"
PDF_OUT = os.path.join(DOCS_DIR, "role2_handover_report.pdf")

pdf = Role2PDF()
pdf.add_page()

# Header Badge
pdf.set_fill_color(220, 252, 231)
pdf.set_text_color(5, 150, 105)
pdf.set_font("helvetica", "B", 8.5)
pdf.cell(52, 6, "  ROLE 2 OFFICIAL HANDOVER  ", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(3)

# Main Title
pdf.set_font("helvetica", "B", 18)
pdf.set_text_color(15, 23, 42)
pdf.multi_cell(0, 8, "Wi-Fi CSI Signal Processing & Feature Engineering")
pdf.set_font("helvetica", "I", 10)
pdf.set_text_color(71, 85, 105)
pdf.cell(0, 6, "Senior Graduation Project: Sensing People Without Seeing Them", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(4)

# Metadata Grid
pdf.set_fill_color(248, 250, 252)
pdf.set_draw_color(226, 232, 240)
pdf.rect(15, pdf.get_y(), 180, 18, style="FD")
cur_y = pdf.get_y() + 2

pdf.set_xy(18, cur_y)
pdf.set_font("helvetica", "B", 7.5)
pdf.set_text_color(100, 116, 139)
pdf.cell(42, 4, "AUTHOR / ROLE", new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 4, "RECIPIENT TEAM", new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 4, "STATUS", new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 4, "MASTER DATASET", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

pdf.set_xy(18, cur_y + 5)
pdf.set_font("helvetica", "B", 8.5)
pdf.set_text_color(15, 23, 42)
pdf.cell(42, 5, "Mohammed Sabry", new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 5, "ML Team & Project Lead", new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 5, "100% Complete & Validated", new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 5, "data/extracted_features.csv", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

pdf.set_y(cur_y + 16)

# Stat Cards
card_w = 42
card_h = 14
gap = 4
stat_y = pdf.get_y()
stats = [
    ("58.7 Hz", "SAMPLING RATE"),
    ("116 Tones", "ACTIVE SUBCARRIERS"),
    ("656 Samples", "EXTRACTED WINDOWS"),
    ("22 Feats", "DIMENSIONS / WIN")
]

for i, (val, lbl) in enumerate(stats):
    x = 15 + i * (card_w + gap)
    pdf.set_fill_color(239, 246, 255)
    pdf.set_draw_color(191, 219, 254)
    pdf.rect(x, stat_y, card_w, card_h, style="FD")
    pdf.set_xy(x, stat_y + 1.5)
    pdf.set_font("helvetica", "B", 10.5)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(card_w, 5, val, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(x, stat_y + 7.5)
    pdf.set_font("helvetica", "B", 6.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(card_w, 4, lbl, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

pdf.set_y(stat_y + card_h + 6)

# Section 1: Executive Summary
pdf.chapter_title("1. Executive Summary & Role Mandate")
pdf.body_p(
    "As Role 2 (Signal Processing & Feature Engineering), my responsibility is to transform raw, noisy 802.11n Wi-Fi Channel "
    "State Information (CSI) measurements collected by commercial ESP32 transceivers into clean, stationary, human-motion-isolated "
    "waveforms, and extract a rich, standardized feature matrix ready for machine learning (Role 3)."
)
pdf.bullet("6-Stage DSP Cleaning Pipeline: ", "Eliminates static DC reflection, dead subcarriers, impulse noise, and high-frequency interference (tools/clean_csi_pipeline.py).")
pdf.bullet("Empirical Validation Proof: ", "Demonstrated clean physical separation between Empty Room, Walking, Sitting, and Hand Wave (tools/plot_30s_validation.py).")
pdf.bullet("Feature Extraction Engine: ", "1.5s sliding window generator extracting 22 time-domain, Doppler, and spatial features (tools/extract_features.py).")
pdf.bullet("Master ML Dataset: ", "656 fully labeled feature vectors with 0 missing/NaN values across 4 classes (data/extracted_features.csv).")

# Section 2: Physical Sensing Testbed
pdf.ln(3)
pdf.chapter_title("2. Physical Sensing Testbed Parameters")

col_widths = [50, 45, 85]
row_h = 6

pdf.set_font("helvetica", "B", 8)
pdf.set_fill_color(241, 245, 249)
pdf.set_text_color(15, 23, 42)
pdf.cell(col_widths[0], row_h, " Parameter", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(col_widths[1], row_h, " Value", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(col_widths[2], row_h, " Technical Context", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

testbed_data = [
    ("Transmitter (TX Node)", "ESP32-WROOM-32 (Ali)", "Broadcasts 60 Hz beacons on Ch 11 (2.462 GHz)"),
    ("Receiver (RX Node)", "ESP32-WROOM-32 (Sabi)", "Station client connected to router; streams UDP"),
    ("Wi-Fi Modulation", "802.11n HT20 (20 MHz)", "Carrier wavelength lambda = 12.2 cm (RF multipath)"),
    ("Packet Rate (fs)", "58.7 packets/sec", "Mean interval dt = 17.03 ms (>98.2% delivery reliability)"),
    ("Raw Subcarriers", "128 Complex (I/Q) Pairs", "Decoded to magnitude A = sqrt(I^2 + Q^2)"),
    ("Active Subcarriers", "116 Communication Tones", "11 dead guard & central DC null tones dropped")
]

pdf.set_font("helvetica", "", 8)
pdf.set_text_color(51, 65, 85)
for p, v, c in testbed_data:
    pdf.cell(col_widths[0], row_h, f" {p}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(col_widths[1], row_h, f" {v}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(col_widths[2], row_h, f" {c}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

# PAGE 2: 6-Stage Pipeline
pdf.add_page()
pdf.chapter_title("3. The 6-Stage DSP Cleaning Pipeline")
pdf.body_p(
    "Indoor Wi-Fi signals decompose into static reflection and dynamic human multipath: H(f,t) = H_static + H_dynamic(t). "
    "The 6-stage pipeline strips H_static and out-of-band noise, isolating H_dynamic(t):"
)

# Embedded Figure: Signal Cleaning Stages
img_stages = os.path.join(DOCS_DIR, "signal_cleaning_stages.png")
if os.path.exists(img_stages):
    pdf.image(img_stages, x=15, w=180)
    pdf.ln(2)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, "Figure 1: Progressive traces through the 6-stage digital signal processing pipeline.", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

stages = [
    ("Stage 1: Complex Demodulation & Subcarrier 0 Drop", 
     "Decodes signed 8-bit bytes to amplitude A = sqrt(I^2 + Q^2). Discards subcarrier 0 to remove AGC settling transients and local oscillator carrier feedthrough."),
    ("Stage 2: Dead Guard & DC Null Masking", 
     "Identifies and drops 11 unmodulated tones [27..35, 94, 96] with mean energy < 1.0, preserving 116 active communication channels without division-by-zero risk."),
    ("Stage 3: Vectorized Hampel Outlier Despiking", 
     "Computes rolling Median Absolute Deviation (MAD, k=7) to replace transmission impulse bursts and packet corruption spikes with local medians (< 0.2s runtime)."),
    ("Stage 4: Zero-Phase Butterworth Bandpass Filter (0.2 Hz - 10.0 Hz)", 
     "4th-order bidirectional digital filter (filtfilt) that eliminates 0 Hz static DC reflections from stationary walls and suppresses high-frequency noise > 10 Hz, strictly isolating human limb/torso Doppler frequencies (0.5 - 5.0 Hz)."),
    ("Stage 5: Multi-Subcarrier Spatial PCA Motion Fusion", 
     "Computes SVD across all 116 subcarriers to project coherent multi-channel motion energy into the dominant PC1 motion profile (> 55% variance explained) and secondary PC2 orthogonal dynamics.")
]

for title, desc in stages:
    pdf.set_font("helvetica", "B", 8.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(0, 4.2, desc)
    pdf.ln(1.5)

# PAGE 3: Empirical Validation
pdf.add_page()
pdf.chapter_title("4. Empirical Validation: Raw vs. Cleaned Waveforms")
pdf.body_p(
    "To validate the pipeline, 1-minute controlled recordings of Empty Room and Person Walking were captured and processed:"
)

# Raw Figure
img_raw = os.path.join(DOCS_DIR, "30s_raw_comparison.png")
if os.path.exists(img_raw):
    pdf.section_title("4.1 Raw CSI Signals (Before Filtering)")
    pdf.image(img_raw, x=15, w=180)
    pdf.ln(1)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, "Figure 2: Raw CSI Carrier Amplitude for Empty Room (top) vs. Person Walking (bottom).", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

# Cleaned Figure
img_clean = os.path.join(DOCS_DIR, "30s_cleaned_comparison.png")
if os.path.exists(img_clean):
    pdf.section_title("4.2 Final Cleaned CSI Signals (After 6-Stage Pipeline)")
    pdf.image(img_clean, x=15, w=180)
    pdf.ln(1)
    pdf.set_font("helvetica", "I", 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, "Figure 3: Cleaned CSI Motion Profile (PC1) for Empty Room (top) vs. Person Walking (bottom).", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

# Metrics Table
pdf.set_font("helvetica", "B", 8)
pdf.set_fill_color(241, 245, 249)
pdf.set_text_color(15, 23, 42)
pdf.cell(45, 6, " Performance Metric", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(40, 6, " Empty Room", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 6, " Person Walking", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(50, 6, " Physical Interpretation", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

metrics_data = [
    ("Baseline Center", "0.00", "0.00", "Static DC carrier stripped cleanly"),
    ("Motion Energy (std)", "8.62", "11.45", "Significant Doppler energy amplification"),
    ("Peak-to-Peak (PTP)", "Quiet baseline", "74.50 (Coherent)", "Multipath phase crests clearly visible"),
    ("Doppler Periodicity", "None", "1.2 - 2.5 Hz", "Exact human walking cadence isolated"),
    ("Average RSSI", "-74.5 dBm", "-71.1 dBm", "Body scatter increases received power")
]

pdf.set_font("helvetica", "", 8)
pdf.set_text_color(51, 65, 85)
for m, e, w, r in metrics_data:
    pdf.cell(45, 5.5, f" {m}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(40, 5.5, f" {e}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(45, 5.5, f" {w}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(50, 5.5, f" {r}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

# PAGE 4: Feature Extraction & Handover
pdf.add_page()
pdf.chapter_title("5. Feature Engineering Engine (tools/extract_features.py)")
pdf.body_p(
    "Cleaned waveforms are partitioned into 1.5-second sliding windows (90 packets) with a 0.5-second step (66% overlap), "
    "extracting 22 statistical, spectral, and spatial features per window:"
)

feat_cols = [45, 65, 70]
pdf.set_font("helvetica", "B", 7.8)
pdf.set_fill_color(241, 245, 249)
pdf.set_text_color(15, 23, 42)
pdf.cell(feat_cols[0], 5.5, " Feature Domain", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(feat_cols[1], 5.5, " Feature Keys", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(feat_cols[2], 5.5, " Physical Sensing Significance", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

feat_data = [
    ("Time-Domain (PC1)", "pc1_var, std, mad, iqr, ptp", "Kinetic motion energy, amplitude spread, stride range"),
    ("Wave Dynamics (PC1)", "pc1_skew, kurt, rms, zcr", "Wave asymmetry, impact sharpness, oscillation rate"),
    ("Time-Domain (PC2)", "pc2_var, std, mad, ptp", "Secondary orthogonal dynamics (limb vs torso)"),
    ("Frequency Doppler", "dominant_freq, spectral_entropy", "Gait cadence frequency (~1.8 Hz) and spectral spread"),
    ("Sub-band Energy", "energy_low, energy_mid, energy_high", "0.2-1.5 Hz (torso), 1.5-4 Hz (legs), 4-10 Hz (rapid)"),
    ("Spatial Cross-Carrier", "sub_var_mean, sub_var_std", "Variance dispersion across 116 subcarriers"),
    ("Signal Power", "rssi_mean, rssi_std", "Average power level and multipath fading depth")
]

pdf.set_font("helvetica", "", 7.5)
pdf.set_text_color(51, 65, 85)
for d, k, s in feat_data:
    pdf.cell(feat_cols[0], 5.2, f" {d}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(feat_cols[1], 5.2, f" {k}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(feat_cols[2], 5.2, f" {s}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

pdf.ln(4)
pdf.chapter_title("6. Master Dataset & Handover to Role 3 (ML)")
pdf.body_p(
    "The processed dataset is saved in data/extracted_features.csv containing 656 fully labeled observations with 0 missing values:"
)

# Class Breakdown Table
pdf.set_font("helvetica", "B", 7.8)
pdf.set_fill_color(241, 245, 249)
pdf.set_text_color(15, 23, 42)
pdf.cell(45, 5.5, " Activity Class", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 5.5, " Window Count", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 5.5, " Class Proportion", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
pdf.cell(45, 5.5, " Sensing Signature", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

class_data = [
    ("Walking", "265 samples", "40.4%", "Strong Doppler waves (1.5 - 2.5 Hz), high PTP"),
    ("Empty Room", "215 samples", "32.8%", "Zero baseline, low variance, flat spectrum"),
    ("Sitting (Still)", "120 samples", "18.3%", "Static attenuation, micro-breathing (0.2-0.35 Hz)"),
    ("Hand Wave", "56 samples", "8.5%", "High local antenna variance, rapid burst energy")
]

pdf.set_font("helvetica", "", 7.5)
pdf.set_text_color(51, 65, 85)
for c, w, p, s in class_data:
    pdf.cell(45, 5.2, f" {c}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(45, 5.2, f" {w}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(45, 5.2, f" {p}", border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(45, 5.2, f" {s}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

pdf.ln(3)
pdf.section_title("Role 3 Python Integration Snippet:")

code_text = (
    "import pandas as pd\n"
    "from sklearn.ensemble import RandomForestClassifier\n"
    "from sklearn.model_selection import StratifiedKFold, cross_val_score\n\n"
    "# 1. Load the Role 2 Feature Dataset\n"
    "df = pd.read_csv('data/extracted_features.csv')\n"
    "X = df.drop(columns=['label', 'source_file', 'win_start_t', 'win_end_t'])\n"
    "y = df['label']\n\n"
    "# 2. Train baseline classifier\n"
    "clf = RandomForestClassifier(n_estimators=100, random_state=42)\n"
    "scores = cross_val_score(clf, X, y, cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42))\n"
    "print(f'5-Fold Cross-Validation Accuracy: {scores.mean()*100:.2f}% (+/- {scores.std()*100:.2f}%)')"
)

pdf.set_fill_color(15, 23, 42)
pdf.set_draw_color(30, 41, 59)
pdf.rect(15, pdf.get_y(), 180, 36, style="FD")
pdf.set_xy(18, pdf.get_y() + 2)
pdf.set_font("courier", "", 7.2)
pdf.set_text_color(248, 250, 252)
pdf.multi_cell(174, 3.6, code_text)

pdf.output(PDF_OUT)
print(f"[+] Successfully generated modern PDF Report: {PDF_OUT}")
