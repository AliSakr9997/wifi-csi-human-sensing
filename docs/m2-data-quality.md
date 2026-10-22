# M2 — CSI Data-Quality Report

**Date:** 2026-10-18
**Author:** Embedded & CSI Engineer
**Hardware:** Board 1 = transmitter (`csi_send`, ESP32-D0WD-V3, MAC `1a:00:00:00:00:00`),
Board 3 = receiver (`csi_recv`, ESP32-D0WD-V3, COM4)
**Firmware:** `espressif/esp-csi` → `examples/get-started/{csi_send,csi_recv}`
**Toolchain:** ESP-IDF v5.4.4, target `esp32`
**Tools:** `tools/csi_capture.py` (logger), `tools/csi_analyze.py` (analysis)

---

## 1. Purpose
Establish, before any signal processing or ML, whether the CSI stream on our hardware is
**sound and reproducible**: stable packet rate, monotonic timestamps, constant framing,
and quantified packet loss. This is the gate for M3 (three-condition feasibility).

---

## 2. Method
Two 60-second captures on the same physical setup, analysing the receiver stream:

| Run | Config | File |
|---|---|---|
| **Run 1** | HT40, send rate 100 pkt/s, console 921600 | `data/csi_run1.csv` |
| **Run 2** | HT20, send rate 60 pkt/s, console 921600 | `data/csi_run2_ht20_60hz.csv` |

```powershell
python tools/csi_capture.py COM4 60 data/csi_run1.csv
python tools/csi_analyze.py  data/csi_run1.csv
python tools/csi_capture.py COM4 60 data/csi_run2_ht20_60hz.csv
python tools/csi_analyze.py  data/csi_run2_ht20_60hz.csv
```

---

## 3. Results

| Metric | Run 1 (HT40 @ 100/s) | Run 2 (HT20 @ 60/s) | Verdict |
|---|---|---|---|
| Packets captured | 4197 | 3507 | — |
| Effective rate | 70.0 pkt/s | 58.5 pkt/s | ✅ |
| **Sender-seq delivery** | **76.9 %** (1264 lost) | **99.4 %** (22 lost) | ✅ fixed |
| Timestamps monotonic | Yes (0 steps ≤0) | Yes (0 steps ≤0) | ✅ |
| Median device interval | 11.0 ms | 17.0 ms (= 60 pkt/s) | ✅ |
| Interval jitter (std) | 12.2 ms | 1.65 ms | ✅ much tighter |
| Gaps > 3× median | 83 (max 154 ms) | **1** (max 51 ms) | ✅ fixed |
| RSSI | −59.9 ± 1.30 dBm | −59.4 ± 4.22 dBm | ✅ stable-ish |
| Noise floor | −96 | −96 | ✅ |
| `sig_mode` / `mcs` / `rate` | 1 / 0 / 11 | 1 / 0 / 11 | ✅ constant |
| Bandwidth `cwb` | 1 (HT40) | 0 (HT20) | as configured |
| `channel` / secondary | 11 / 2 (below) | 11 / 0 (none) | ✅ |
| CSI payload | 384 int8 = 192 subcarriers | 256 int8 = **128 subcarriers** | constant ✅ |
| `first_word_invalid` | 1 (all packets) | 1 (all packets) | ⚠️ see §5 |
| Empty/zero payloads | 0 | 0 | ✅ real signal |
| Amplitude mean / std | 26.5 / 12.1 | 28.9 / 16.0 | ✅ non-degenerate |

---

## 4. Root-cause of the Run-1 loss
The loss was in the **UART link, not the radio**:

- Average serialised line ≈ 5,523,123 B ÷ 4197 ≈ **1.32 KB/packet**.
- At **921600 baud** the link carries ≈ 92 KB/s → **≈ 70 packets/s ceiling**.
- Run 1 was captured at exactly **70 pkt/s** while the sender produced 100/s → the link
  was saturated and ~23 % of packets were dropped at the serial port.

Run 2 reduced packet size (HT20: 256 vs 384 int8) *and* send rate (60/s), giving plenty
of headroom → **99.4 % delivery** and a far tighter interval distribution.

---

## 5. Caveats carried into M3

1. **`first_word_invalid = 1` on 100 % of packets.** The first CSI word is flagged
   invalid by the driver and must be **discarded from every packet** in the DSP stage
   (typically the first 4 bytes / first ~2 subcarriers). Ignoring this injects a constant
   artefact.
2. **HT20 vs HT40 trade-off.** HT20 gives 128 subcarriers (vs 192) but a healthy link.
   If M3 needs more subcarrier diversity, use **HT40 at ~50–60 pkt/s** (≈ 79 KB/s, still
   under the 92 KB/s ceiling) instead of HT20.
3. **RSSI spread widened** in Run 2 (−80…−49 dBm vs −64…−56). Not yet explained — could be
   ambient movement during that capture. Re-check with a controlled capture in M3.
4. **Serial ceiling is a hard limit.** Classic **CP2102** bridges cap near 921600 baud, so
   baud cannot be the long-term answer for high-rate CSI.

---

## 6. Conclusions
- The CSI stream is **structurally sound and reproducible**: constant framing, monotonic
  timestamps, non-degenerate amplitudes, no corrupt/empty payloads.
- Packet loss was a **serial-throughput** artefact, now resolved (99.4 % delivery) by
  reducing payload and rate.
- **M2 gate passed** for the current single-link, low-rate configuration.

---

## 7. M3 prerequisites / follow-ups

| ID | Item | Why it matters | Priority |
|---|---|---|---|
| **M3-P1** | **Migrate CSI transport from UART to Wi-Fi/UDP** (PC as UDP receiver) | Removes the CP2102/921600 ceiling; the only way to run high-rate / multi-node CSI, as the literature setups do. | **High (M3 prereq)** |
| M3-P2 | Drop the first CSI word in DSP | `first_word_invalid=1` on every packet | High |
| M3-P3 | Decide HT20 (128 subc.) vs HT40 @ 50–60 pkt/s (192 subc.) | Sensitivity vs throughput | Medium |
| M3-P4 | Fix the RX/TX placement + distance (README: > 1 m, external antenna preferred) | Reproducible geometry | Medium |
| M3-P5 | Add a capture metadata file (config, distance, timestamp, room state) per run | Reproducibility | Medium |

---

## 8. Artifacts
- `data/csi_run1.csv` — HT40 @ 100 pkt/s (4197 packets)
- `data/csi_run2_ht20_60hz.csv` — HT20 @ 60 pkt/s (3507 packets)
- `tools/csi_capture.py`, `tools/csi_analyze.py`
- Firmware changes for Run 2: `csi_send/main/app_main.c` (`WIFI_BW_HT20`,
  `WIFI_PHY_MODE_HT20`, `CONFIG_SEND_FREQUENCY 60`) and `csi_recv/main/app_main.c`
  (`WIFI_BW_HT20`, `WIFI_PHY_MODE_HT20`).
