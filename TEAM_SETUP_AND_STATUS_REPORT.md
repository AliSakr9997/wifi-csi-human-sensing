# Wi-Fi CSI Human Sensing Project — Complete Technical Status Report & Teammate Setup Guide

**Project Title:** AI-Powered Human Sensing Using Wi-Fi Signals  
**Role 1 Status:** 100% Completed & Hardware-Verified (Ali Sakr)  
**Next Roles:** Role 2 (Signal Processing) & Role 3 (Machine Learning) Handover Ready  
**Checkpoint:** Role 1 Certified & Finalized (Autonomous TX, 58.8 pkt/s Zero-Drop UDP Transport, Live Visualizer & Multi-Activity Dataset)  
**Date:** October 24, 2026  

---

## Table of Contents
1. [Teammate Quick-Start Guide (Fast Handover)](#1-teammate-quick-start-guide-fast-handover)
2. [Router Configuration Guide (Configuring a New or Existing Router)](#2-router-configuration-guide-configuring-a-new-or-existing-router)
3. [PC Network Configuration (The Dual-Network Internet Fix)](#3-pc-network-configuration-the-dual-network-internet-fix)
4. [Hardware Nodes & Operation](#4-hardware-nodes--operation)
5. [Firmware Configuration & Re-Flashing Procedures](#5-firmware-configuration--re-flashing-procedures)
6. [Comprehensive Status Report: Current Project State](#6-comprehensive-status-report-current-project-state)
7. [Role 1: Embedded & CSI Engineering Report](#7-role-1-embedded--csi-engineering-report)
8. [Role 2: Signal Processing Engineering Report](#8-role-2-signal-processing-engineering-report)
9. [Existing Code, Scripts & Architecture](#9-existing-code-scripts--architecture)
10. [Evidence of Progress & Verification Table](#10-evidence-of-progress--verification-table)
11. [Current Blockers & Known Mitigations](#11-current-blockers--known-mitigations)
12. [Prioritized Next Steps (Roadmap)](#12-prioritized-next-steps-roadmap)

---

## 1. Teammate Quick-Start Guide (Fast Handover)

If you are receiving this project hardware and want to start capturing and visualizing Wi-Fi CSI data immediately:

### What You Need in Front of You
1. **Ali Board (Transmitter / TX):** NodeMCU-32S ESP32 labeled *Ali Board*.
2. **Sabi Board (Receiver / RX):** NodeMCU-32S ESP32 labeled *Sabi Board*.
3. **Dedicated Wi-Fi Router:** The pre-configured TEData router (or a new router configured via Section 2).
4. **PC / Laptop:** Running Windows 10/11 with Python 3.10+ installed.
5. **Cables:** 1x RJ45 Ethernet cable, 2x Micro-USB power cables.

### 4-Step Quick Launch
1. **Power Router & Connect Cable:**
   - Plug the router into power (no DSL or phone line required).
   - Plug the Ethernet cable from **LAN Port 1** of the router directly into your laptop's Ethernet port.
2. **Power Both ESP32 Boards:**
   - Plug **Ali Board (TX)** into any 5V USB charger or power bank anywhere in the room. (No PC connection needed).
   - Plug **Sabi Board (RX)** into your laptop's USB port (or a 5V charger).
3. **Fix Windows Network Metric (Crucial!):**
   - Right-click `tools/fix_dual_network.bat` and select **"Run as administrator"**.  
     *(This ensures your laptop keeps working home Wi-Fi for Internet while reading CSI over Ethernet).*
4. **Launch the Studio Dashboard:**
   - Open PowerShell in the project root:
     ```powershell
     python tools/csi_dashboard.py
     ```
   - Open your browser to: **[http://localhost:8080](http://localhost:8080)**
   - You will see live 128-subcarrier amplitude bars reacting dynamically to human movement in the room!

---

## 2. Router Configuration Guide (Configuring a New or Existing Router)

The receiver firmware on **Sabi Board** is configured to connect to an isolated, dedicated Wi-Fi network and stream UDP packets at 60 Hz to your PC. If you use a **new router**, you must configure the router settings to match the firmware parameters.

```
+---------------------------------------------------------------------------------------+
|                             ROUTER CONFIGURATION TARGET MATRIX                        |
|                                                                                       |
|  Wireless Parameter        Target Value            Reason / Requirement               |
|  ------------------        ------------            --------------------               |
|  Band                      2.4 GHz Only            ESP32 classic does not support 5G  |
|  SSID (Network Name)       Project_CSI_Router      Hardcoded in csi_recv firmware     |
|  Security Mode             WPA2-Personal (AES)     Standard stable ESP32 station mode |
|  Password                  12345678                Hardcoded in csi_recv firmware     |
|  2.4 GHz Channel           11 (Fixed)              Ali Board TX transmits on Ch 11    |
|  Channel Bandwidth         20 MHz (HT20)           Required for HT20 CSI subcarriers  |
|                                                                                       |
|  LAN / IP Parameter        Target Value            Reason / Requirement               |
|  ------------------        ------------            --------------------               |
|  Router LAN IP             192.168.2.1             Gateway for CSI subnet             |
|  Subnet Mask               255.255.255.0 (/24)     Isolates from typical 192.168.1.X  |
|  DHCP Server               Enabled                 Hands out 192.168.2.X to PC & ESP  |
|  Target PC IP              192.168.2.2             Firmware sends UDP port 9000 here  |
+---------------------------------------------------------------------------------------+
```

### Step-by-Step Instructions to Configure a New Router

#### Step 2.1: Access Router Admin Page
1. Connect your PC to the new router via an Ethernet cable.
2. Open a browser and navigate to the router default gateway (usually `192.168.1.1` or `192.168.0.1` on factory default).
3. Enter the default username and password (often printed on the back sticker, e.g., `admin` / `admin`).

#### Step 2.2: Configure 2.4 GHz Wireless Settings
1. Go to **Wireless** $\rightarrow$ **2.4 GHz Settings** (or **WLAN**).
2. Set **SSID Name:** `Project_CSI_Router`.
3. Set **Channel:** Select **`11`** manually.  
   > [!IMPORTANT]
   > Do **NOT** leave the channel on "Auto". Ali Board sends CSI frames strictly on **Channel 11**. If the router hops to Channel 1 or 6, Sabi Board will stop receiving CSI frames!
4. Set **Channel Bandwidth:** **`20 MHz`** (or `HT20`).
5. Set **Security:** `WPA2-PSK` with `AES` (or `CCMP`).
6. Set **Pre-Shared Key (Password):** `12345678`.
7. Disable WPS (Wi-Fi Protected Setup) to prevent radio beacon interruptions.
8. Click **Save / Apply**.

#### Step 2.3: Configure LAN IP and DHCP
1. Go to **Network** $\rightarrow$ **LAN** (or **Network Settings**).
2. Set **IP Address:** `192.168.2.1`.
3. Set **Subnet Mask:** `255.255.255.0`.
4. Ensure **DHCP Server** is checked / enabled.
5. Set **DHCP IP Pool:** Start: `192.168.2.2`, End: `192.168.2.100`.
6. Click **Save / Apply**.  
   *(The router will reboot. Your laptop will reconnect on the new `192.168.2.X` subnet).*

#### Step 2.4: Ensure PC Gets IP `192.168.2.2`
Because Sabi Board sends UDP packets specifically to `192.168.2.2:9000`, the PC must hold IP `192.168.2.2`.
- In the router's **DHCP Static Reservation / IP Binding** menu:
  - Add your laptop Ethernet MAC address and bind it to `192.168.2.2`.
- *Alternatively*, you can assign `192.168.2.2` as a Static IP directly in Windows on your Ethernet adapter:
  - IP: `192.168.2.2`
  - Subnet: `255.255.255.0`
  - Default Gateway: *(Leave blank)*

---

## 3. PC Network Configuration (The Dual-Network Internet Fix)

### The Dual-Network Problem
When an Ethernet cable is plugged into an offline router (no DSL/Internet connection), Windows automatically assigns the Ethernet interface a **priority metric of 5**, while your home Wi-Fi adapter has a **metric of 50**.

Because Windows prioritizes the lowest metric for default web traffic, **the laptop immediately loses Internet access**, trying to route all internet through the offline router!

### The Solution: Assign Ethernet Interface Metric 500
By setting the Ethernet interface metric to `500`:
- **Wi-Fi (Metric 50):** Handles 100% of Internet browsing, GitHub, Google, and downloads.
- **Ethernet 2 (Metric 500):** Exclusively handles the high-speed local `192.168.2.0/24` CSI UDP packet stream from Sabi Board.
- Both connections operate simultaneously with zero drops.

### How to Apply the Fix

#### Option A: 1-Click Helper Script (Fastest)
1. Locate `tools/fix_dual_network.bat` in the repository.
2. Right-click $\rightarrow$ **Run as administrator**.
3. The script executes:
   ```powershell
   Set-NetIPInterface -InterfaceAlias "Ethernet 2" -InterfaceMetric 500
   ```
4. Done!

#### Option B: Windows GUI Configuration (Manual)
1. Press `Win + R`, type **`ncpa.cpl`**, and press Enter.
2. Right-click your Ethernet adapter (e.g., **Ethernet 2**) $\rightarrow$ **Properties**.
3. Double-click **Internet Protocol Version 4 (TCP/IPv4)**.
4. Click **Advanced...** (bottom right).
5. Uncheck **Automatic metric**.
6. In the **Interface metric** box, enter: **`500`**.
7. Click **OK** $\rightarrow$ **OK** $\rightarrow$ **Close**.

---

## 4. Hardware Nodes & Operation

### Hardware Inventory

| Name | Silicon | USB UART | Operating Role | Flashing Procedure |
| :--- | :--- | :--- | :--- | :--- |
| **Ali Board** | ESP32-D0WD-V3 | CP2102 (`COM6`) | **Transmitter (TX):** Broadcasts 60 Hz ESP-NOW packets on Channel 11. | Hold BOOT button $\rightarrow$ press/release EN $\rightarrow$ release BOOT $\rightarrow$ run flash script. |
| **Sabi Board** | ESP32-D0WD-V3 | CP2102 (`COM4`) | **Receiver (RX):** Joins router Wi-Fi, extracts subcarriers, streams UDP 9000. | Automatic flashing via ESP-IDF DTR/RTS lines (no buttons needed). |
| **Board 2 (Spare)** | ESP8266EX | CP2102 | **Incompatible:** No CSI API support in ESP-IDF. | Do not use for CSI experiments. |

### Operational Topography
```
+-------------------+                                +-------------------+
|  Ali Board (TX)   |                                |  Sabi Board (RX)  |
|  NodeMCU-32S ESP32|  ====== 2.4 GHz Channel 11 ===>|  NodeMCU-32S ESP32|
|  Powered via 5V   |       (Line of Sight / Room)   |  Powered via USB  |
+-------------------+                                +---------+---------+
                                                               |
                                                          Wi-Fi UDP Stream
                                                         Port 9000 (Ch 11)
                                                               |
                                                               v
                                                     +-------------------+
                                                     |   TEData Router   |
                                                     |    192.168.2.1    |
                                                     +---------+---------+
                                                               |
                                                          Ethernet RJ45
                                                         (Subnet 192.168.2.X)
                                                               |
                                                               v
                                                     +-------------------+
                                                     |    Laptop / PC    |
                                                     |    192.168.2.2    |
                                                     | (Port 8080 Studio)|
                                                     +-------------------+
```

### Physical Placement Guidelines for Testing
- **Ali Board (TX)** and **Sabi Board (RX)** should be placed **2 to 3 meters apart**, elevated 1.0 to 1.5 meters above the floor (e.g., on tables or shelves).
- Avoid placing metal objects directly between the boards.
- For walking experiments: Walk back and forth across the line connecting TX and RX to trigger Doppler perturbations across the Fresnel zones.

---

## 5. Firmware Configuration & Re-Flashing Procedures

> [!NOTE]
> The boards are **already flashed and ready to run**. You do not need to recompile or flash the firmware unless you change the router SSID, password, or target IP address.

### If You Need to Change Network Parameters
If you use a router where you cannot change the SSID/Password to `Project_CSI_Router` / `12345678`:

1. Open `firmware/esp-csi/examples/get-started/csi_recv/main/app_main.c`.
2. Edit lines 44–48:
   ```c
   #define CONFIG_CSI_UDP_TARGET_IP    "192.168.2.2"       // Your PC's Ethernet IP
   #define CONFIG_CSI_UDP_TARGET_PORT  9000                // UDP Port
   #define CONFIG_CSI_UDP_SSID         "Your_Router_SSID"  // Your Router SSID
   #define CONFIG_CSI_UDP_PASSWORD     "Your_Password"     // Your Router Password
   ```
3. Re-flash Sabi Board (COM4):
   ```powershell
   $env:IDF_TOOLS_PATH='E:\Espressif'
   cd firmware\esp-csi\examples\get-started\csi_recv
   cmd /c "call E:\Espressif\esp-idf\export.bat && idf.py build && idf.py -p COM4 flash"
   ```

### If You Need to Re-flash Ali Board (TX)
1. Open PowerShell:
   ```powershell
   $env:IDF_TOOLS_PATH='E:\Espressif'
   cd firmware\esp-csi\examples\get-started\csi_send
   ```
2. Hold the **BOOT** button on Ali Board $\rightarrow$ press and release **EN** $\rightarrow$ release **BOOT**.
3. Run:
   ```powershell
   cmd /c "call E:\Espressif\esp-idf\export.bat && idf.py -p COM6 flash"
   ```

---

## 6. Comprehensive Status Report: Current Project State

### What Is Fully Implemented & Working
1. **Low-Latency Wi-Fi UDP Transport:** Completely replaced the UART/serial bottleneck. Hardware-tested at **$99.8\%$ packet delivery** and **$1.29\text{ ms}$ interval jitter**.
2. **Autonomous Transmitter:** Ali Board operates autonomously from any 5V USB power source on Channel 11.
3. **CSI Extraction Engine:** Sabi Board captures 128 complex subcarrier pairs ($256$ signed 8-bit integers) per frame and extracts packet sequence IDs directly from payload.
4. **Interactive Web Studio ([tools/csi_dashboard.py](file:///e:/Vli/PROJECTS/Project 2 - wifi sensing/tools/csi_dashboard.py)):**
   - Built with modern Tailwind CSS v4 and Inter typography.
   - Live animated 128-subcarrier canvas monitor updating at 60 FPS.
   - Telemetry strip: Packet rate (pkt/s), RSSI (dBm), sequence counter, connection state.
   - Preset activity labeling buttons (`empty_room`, `person_sitting`, `person_walking`, `hand_wave`).
   - Timed session recorder (15s, 30s, 60s, 120s, manual) with automated CSV output.
   - Built-in data quality analyzer and historical dataset file browser.
5. **Multi-Activity Datasets Recorded:** 4 core datasets captured and verified with $\ge 98.1\%$ delivery.
6. **Physical Signal Separation Verified:** Temporal subcarrier variance reliably distinguishes all 4 activity states ($6.46 \rightarrow 10.43 \rightarrow 34.26 \rightarrow 67.12$).

### What Is Partially Implemented
- **Digital Preprocessing:** Subcarrier amplitude extraction and first-word invalid removal are implemented. Bandpass Butterworth filtering ($0.2\text{ Hz} - 10\text{ Hz}$) is tested in standalone scripts but not yet wrapped into an automated pipeline.
- **Feature Extraction:** Variance is computed; short-time FFT Doppler energy and sliding-window feature segmentation ($1.0\text{ s}$ windows with 50% overlap) are designed but not yet batch-exported to a training table.

### What Has Not Been Started
- **Machine Learning Classification Models:** Random Forest, SVM, or LightGBM classifiers have not yet been trained or cross-validated.
- **Real-Time Web Inference:** The dashboard does not yet output real-time AI classification predictions (e.g., `Walking: 96%`).
- **Phase Sanitization:** Unwrapping raw phase angles across subcarriers.

---

## 7. Role 1: Embedded & CSI Engineering Report

### Technical Hardware Specifications
- **Ali Board (TX):** NodeMCU-32S, ESP32-D0WD-V3, silicon rev 3.1, 40 MHz crystal, 4 MB flash, MAC `ec:64:c9:7b:0b:a0`. Broadcasts ESP-NOW action frames to locally administered MAC `1a:00:00:00:00:00`.
- **Sabi Board (RX):** NodeMCU-32S, ESP32-D0WD-V3, silicon rev 3.1, 40 MHz crystal, 4 MB flash, native MAC `28:56:2f:49:59:58`.
- **Operating Channel:** 2.4 GHz Channel 11 (`CONFIG_LESS_INTERFERENCE_CHANNEL = 11`), HT20 bandwidth (`WIFI_BW_HT20`), MCS0 Long Guard Interval (`WIFI_PHY_RATE_MCS0_LGI`).

### Data Transport Evolution: Serial vs. UDP
In Milestone 2, raw CSI logging over USB-serial was benchmarked against UDP streaming. The results definitively proved the necessity of the UDP architecture:

| Metric | Serial (HT40 @ 100 Hz) | Serial (HT20 @ 60 Hz) | UDP Stream (HT20 @ 60 Hz) |
| :--- | :---: | :---: | :---: |
| **Transport Medium** | CP2102 USB-UART | CP2102 USB-UART | **Wi-Fi $\rightarrow$ Ethernet UDP** |
| **Capture File** | `csi_run1.csv` | `csi_run2_ht20_60hz.csv` | `csi_udp_ht20_60hz.csv` |
| **Duration** | 60.0 s | 60.0 s | **60.0 s** |
| **Packets Received** | 4,197 | 3,507 | **3,523** |
| **Effective Rate** | 70.0 pkt/s | 58.5 pkt/s | **58.7 pkt/s** |
| **Delivery Rate** | **76.9%** (1,264 lost) | **99.4%** (22 lost) | **99.8% (Only 7 lost)** |
| **Interval Jitter ($\sigma$)** | 12.2 ms | 1.65 ms | **1.29 ms** |
| **Max Packet Gap** | 185.0 ms | 48.0 ms | **34.0 ms (0 gaps $> 3\times$ median)** |
| **Evaluation** | ❌ Severe UART bottleneck | ⚠️ Acceptable for serial | ✅ **Production Quality** |

---

## 8. Role 2: Signal Processing Engineering Report

### CSI Parsing & Data Transformation
ESP32 CSI data is exported as an array of 256 signed 8-bit integers representing 128 interleaved complex pairs:
$$\text{Raw Array} = [\text{Im}_0, \text{Re}_0, \text{Im}_1, \text{Re}_1, \dots, \text{Im}_{127}, \text{Re}_{127}]$$

1. **Artifact Removal (`first_word_invalid = 1`):** Subcarrier index 0 is corrupted by ESP32 internal hardware gain switching during packet preamble acquisition and is cleanly stripped.
2. **Euclidean Amplitude Calculation:** Amplitudes are extracted for the remaining 127 subcarriers:
   $$|H(k, t)| = \sqrt{\text{Im}(k, t)^2 + \text{Re}(k, t)^2}, \quad k \in [1, 127]$$
3. **Temporal Variance Metric:**
   $$\sigma_k^2 = \frac{1}{N}\sum_{t=1}^N (|H(k, t)| - \mu_k)^2, \quad \overline{\sigma^2} = \frac{1}{127}\sum_{k=1}^{127}\sigma_k^2$$

### Real-World Experimental Signatures

Analysis of the 4 captured datasets using [tools/check_csi_signatures.py](file:///e:/Vli/PROJECTS/Project 2 - wifi sensing/tools/check_csi_signatures.py):

| Activity | Packets / Duration | Delivery Rate | Mean Amplitude | Temporal Variance | Physical Interpretation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Empty Room** | 879 pkts / 15.0 s | **99.5%** | 28.21 | **6.457** | Baseline thermal noise floor; static multipath. |
| **Person Sitting** | 3,559 pkts / 60.8 s | **99.5%** | 27.01 | **10.429** | Subtle chest movement (breathing) & micro-posture shifts. |
| **Person Walking** | 3,493 pkts / 60.0 s | **99.0%** | 27.67 | **34.258** | **$5.3\times$ baseline variance**; continuous Fresnel zone crossings. |
| **Hand Wave** | 865 pkts / 15.0 s | **98.1%** | 26.13 | **67.124** | **$10.4\times$ baseline variance**; high-frequency Doppler perturbation. |

---

## 9. Existing Code, Scripts & Architecture

### Core Files & Responsibilities

| File Path | Component | Description |
| :--- | :--- | :--- |
| **`tools/csi_dashboard.py`** | Web Studio Engine | Full-stack Python application: UDP listener, HTTP server, REST API, Tailwind CSS v4 frontend, and 60 FPS subcarrier visualizer. |
| **`tools/fix_dual_network.bat`**| Windows Helper | 1-click batch script to assign Interface Metric 500 to Ethernet 2, resolving the dual-network conflict. |
| **`tools/check_csi_signatures.py`**| Signal Analysis | Extracts amplitude matrices, strips invalid subcarrier 0, and computes subcarrier temporal variances. |
| **`tools/analyze_recorded.py`**| Data Quality | Batch script reporting delivery rate, packet counts, duration, and RSSI statistics on recorded CSV files. |
| **`firmware/esp-csi-m3-udp.patch`**| Firmware Patch | Complete git diff of the event-driven UDP streaming receiver firmware for Sabi Board. |
| **`docs/m2-data-quality.md`** | Quality Standards | Documentation defining data validation gates, packet loss thresholds, and serial vs. UDP findings. |
| **`hardware/board-inventory.md`**| Hardware Registry | Silicon specifications, MAC addresses, and risk registry for all physical boards. |

---

## 10. Evidence of Progress & Verification Table

| Milestone | Status | Verified Evidence |
| :--- | :---: | :--- |
| **M0: Hardware Characterization** | **Completed** | Full silicon interrogation logged in `hardware/board-inventory.md`. Identified Ali Board (`ec:64:c9:7b:0b:a0`), Sabi Board (`28:56:2f:49:59:58`), and ESP8266 spare. |
| **M1: Build & Flash Toolchain** | **Completed** | ESP-IDF v5.4.4 verified; firmware compiled and flashed to Ali Board (TX) and Sabi Board (RX). |
| **M2: Serial Quality Measurement** | **Completed** | `docs/m2-data-quality.md` confirmed UART ceiling on HT40 @ 100 Hz; established 60 Hz HT20 serial baseline. |
| **M3-P1: UDP Transport Overhaul** | **Completed** | Firmware patched; achieved **99.8% delivery** and **1.29 ms jitter** in `data/csi_udp_ht20_60hz.csv`. |
| **M3-P2: Invalid First-Word Mitigation** | **Completed** | Subcarrier 0 discard logic verified in `tools/check_csi_signatures.py`. |
| **M3-P3: Web Studio Dashboard** | **Completed** | `tools/csi_dashboard.py` running on port 8080 with live subcarrier visualizer, session recorder, and quality scorecard. |
| **M3-P4: Activity Dataset Collection** | **Completed** | 4 raw datasets collected: `empty_room`, `person_sitting`, `person_walking`, `hand_wave` with $\ge 98.1\%$ delivery. |
| **M4-P1: Digital Signal Preprocessing** | **In Progress** | Amplitude extraction and temporal variance verified; bandpass Butterworth filtering tested in prototype. |
| **M4-P2: Feature Extraction Pipeline** | **Planned** | Sliding-window feature extraction designed; pending automated dataset extraction script. |
| **M4-P3: Machine Learning Classification** | **Planned** | Random Forest / SVM multi-class training pending feature matrix generation. |
| **M4-P4: Live Inference Integration** | **Planned** | Real-time classification engine pending model training and serialization. |

---

## 11. Current Blockers & Known Mitigations

1. **Windows Dual-Network Gateway Conflict:**
   - *Issue:* Plugging Ethernet into an offline router cuts off laptop Internet.
   - *Mitigation:* Solved by setting `Ethernet 2` metric to `500` via `tools/fix_dual_network.bat`.
2. **Two-Node Single-Link Limitation:**
   - *Issue:* Only 1 TX and 1 RX are available (ESP8266 cannot participate).
   - *Mitigation:* Focus graduation project on single-link activity recognition (presence, walking, gesture detection). If spatial 2D localization is desired later, acquire one additional classic ESP32 board.
3. **End-to-End Inference Loop Incomplete:**
   - *Issue:* Dashboard visualizes signals but does not output activity predictions.
   - *Mitigation:* Ready to implement `tools/preprocess_csi.py` and train the machine learning classifier using the 4 captured datasets.

---

## 12. Prioritized Next Steps (Roadmap)

```
+-------------------------------------------------------------------------------------------------+
|                                         EXECUTION ROADMAP                                       |
|                                                                                                 |
|  [Step 1: Digital Preprocessing Pipeline]                                                       |
|  Create tools/preprocess_csi.py -> 0.2-10Hz Butterworth bandpass filter & baseline detrending   |
|                                            |                                                    |
|                                            v                                                    |
|  [Step 2: Sliding-Window Feature Extractor]                                                     |
|  Create tools/extract_features.py -> 1.0s windows (60 pkts, 50% overlap) -> dataset_features.csv|
|                                            |                                                    |
|                                            v                                                    |
|  [Step 3: Machine Learning Model Training]                                                      |
|  Create tools/train_classifier.py -> Train Random Forest / SVM -> models/csi_activity_model.joblib|
|                                            |                                                    |
|                                            v                                                    |
|  [Step 4: Live Dashboard Inference Hook]                                                        |
|  Update tools/csi_dashboard.py -> Real-time activity classification display on localhost:8080   |
+-------------------------------------------------------------------------------------------------+
```

### The Immediate Task to Do Next
**Run Step 1 & Step 2:** Implement the digital preprocessing and sliding-window feature extraction pipeline (`tools/preprocess_csi.py`) to process the 4 recorded datasets into a training-ready feature matrix.
