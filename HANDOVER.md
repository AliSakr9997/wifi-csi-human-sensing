# Wi-Fi CSI Human-Sensing Project — Handover

> Handover for a friend continuing this project. Milestones M0–M2 are complete and verified;
> M3 is planned but not started. Read this file top-to-bottom before touching anything.

## 1. Scope

Monitor human presence / activity in a room **without cameras or microphones**, using Wi-Fi
Channel State Information (CSI) captured between two low-cost boards. The core ideas:

- **Transmit node** sends a continuous packet stream (known payload, fixed PHY rate).
- **Receive node** measures per-packet CSI amplitude/phase and logs it over USB serial.
- **Controller (PC)** runs capture scripts, timestamps packets, and writes CSV; a
  data-quality report (`docs/m2-data-quality.md`) defines what makes a run usable.
- Later milestones (M3+) are about cleaning the measurement (drop-rate, transport,
  geometry) and then going from raw CSI to labelled classification.

## 2. Hardware inventory (measured, not assumed)

The shipped study proposal assumed 3x ESP32-S3-DevKitC-1. Reality differs; everything
below was measured, not taken from the proposal.

### Board 1 — CSI transmitter (ESP32)
- Chip: ESP32-D0WD-V3, silicon rev v3.1
- Flash: 4 MB, crystal: 40 MHz
- MAC (burned): `ec:64:c9:7b:0b:a0`
- Configured soft STA MAC: `1a:00:00:00:00:00` (locally administered)
- USB bridge: CP2102 on **COM4**
- **Download mode via BOOT button only** — the board does not drop into the ROM
  bootloader by itself. Always do: hold BOOT → press and release EN → release BOOT,
  then run `tools\board-flashing\flash_b1_send.py`. Details in §6.
- Role: transmitter only.

### Board 2 — spare (ESP8266, not CSI-capable)
- Chip: ESP8266EX, crystal: 26 MHz
- MAC: `2c:f4:32:18:fd:b3`
- **Do not use for CSI.** The ESP8266 has no CSI receiver API in ESP-IDF; its
  legacy "CSI" interface cannot reproduce the merged subcarrier data the ESP32 gives.
- Role: plain transmitter / spare only.

### Board 3 — CSI receiver (ESP32)
- Chip: ESP32-D0WD-V3, silicon rev v3.1
- MAC: `28:56:2f:49:59:58`
- USB bridge: CP2102 on **COM4** (same port used in tests; other COMs exist too, but
  scripts were verified against COM4)
- Download mode: **automatic** when the ESP-IDF flasher connects (no button sequence
  needed normally).
- Role: receiver; its serial output is the CSI capture stream.

=> With only these boards, **2 simultaneous CSI nodes** are available (1 TX + 1 RX).
A 3- or 4-node experiment needs a purchase (see §10).

## 3. Toolchain / environment

- ESP-IDF **v5.4.4** at `E:\Espressif\esp-idf`
- `IDF_TOOLS_PATH=E:\Espressif`
- On Windows PowerShell, the canonical way to invoke idf.py is:
  ```powershell
  $env:IDF_TOOLS_PATH='E:\Espressif'
  cmd /c "call E:\Espressif\esp-idf\export.bat && idf.py <cmd>"
  ```
- `firmware/esp-csi` is **not committed to this repo** (see `.gitignore`). It is an
  external clone of https://github.com/espressif/esp-csi. Re-clone it there if you
  need to regenerate; the built `sdkconfig*` / build outputs are not needed to
  reproduce the analysis below, but are needed to rebuild the firmware.

## 4. Firmware config (measured source facts)

Path prefixes below are `firmware/esp-csi/examples/get-started/`.

### csi_send/main/app_main.c (transmitter)
- Channel: `CONFIG_LESS_INTERFERENCE_CHANNEL` = 11
- PHY mode: `WIFI_PHY_MODE_HT20`
- Rate: `WIFI_PHY_RATE_MCS0_LGI`
- Frame frequency: `CONFIG_SEND_FREQUENCY` = 60 packets/s
- Target STA MAC: `1a:00:00:00:00:00`
- Older/vendor-derived branches: C5/C61/C6 use `WIFI_BAND_MODE_2G_ONLY` +
  HT40/11N; the classic-ESP32 branch uses `CONFIG_WIFI_BANDWIDTH = WIFI_BW_HT20`.

### csi_recv/main/app_main.c (receiver)
- Same ch 11 / HT20 / `WIFI_PHY_RATE_MCS0_LGI`, matching the TX so patterns line up.
- `CONFIG_FORCE_GAIN = 0` (AGC on by default)
- Includes `esp_csi_gain_ctrl.h`
- C5/C61 vendor branches add `CSI_FORCE_LLTF = 0`.

### csi_recv_router
- Likely an **unmodified** reference example; not changed during M0–M2.
- Use it as a reference if you want a third-party / router CSI node later.

## 5. M0–M2: what was actually done and what it proves

### M0 — Physical bring-up
- Identified all three boards (chip revs, MACs, crystal sizes, USB bridges).
- Plain-data path over the CP2102 USB↔UART is proven on both ESP32 boards.
- Discovered Board 1's BOOT-button-only bootloader entrance (see §6).

### M1 — Firmware build & flash
- Built the `esp-csi/get-started` examples for the **classic ESP32** target
  (`idf.py set-target esp32`, not esp32s3).
- Flashed csi_send to Board 1 and csi_recv to Board 3.
- Confirm the RX serial banner / keepalives before starting a long capture.

### M2 — Data-quality measurement (the definitive baseline)
Report: `docs/m2-data-quality.md`. Two "clean-CSI" runs were compared:

| | Run 1 (HT40, 100 pkt/s) | Run 2 (HT20, 60 pkt/s) |
|---|---|---|
| CSV | `data/csi_run1.csv` | `data/csi_run2_ht20_60hz.csv` |
| Packets received | 4197 | 3507 |
| Effective rate | 70.0 pkt/s | 58.5 pkt/s |
| Delivery rate | 76.9% (1264 lost) | **99.4%** (22 lost) |
| Median interval | 11.0 ms | 17.0 ms |
| Interval jitter (σ) | 12.2 ms | **1.65 ms** |

**Verdict: HT20 @ 60 pkt/s is the M2 baseline.** It is the configuration to keep
unless M3 shows a reason to change it. Run 1 (HT40 @ 100 pkt/s) is the reference
"bad case" — large delivery loss and jitter caused by USB-serial bandwidth
pressure, a known hardware limitation (risk H-09).

Reference data-quality gates to treat a run as valid: effective rate close to the
configured rate, near-100% delivery, small interval jitter, and a stable
packet-to-packet histogram in `tools/csi_analyze.py` output.

## 6. Reproduction — how to repeat M1 / M2 from a clean checkout

### 6.1 Environment
Open PowerShell in the repo root, then set:
```powershell
$env:IDF_TOOLS_PATH='E:\Espressif'
```
After every shell restart, this variable has to be set again before using idf.py.

### 6.2 Rebuild / re-flash firmware (only if needed; the flashed boards already work)
```powershell
cd firmware\esp-csi
cmd /c "call E:\Espressif\esp-idf\export.bat && idf.py set-target esp32 && idf.py build && idf.py -p COM4 flash"
```
- **Board 1 (TX)**: hold BOOT → tap EN → release BOOT → run the flash command.
  If the flash fails with `Timed out waiting for packet header` the BOOT button
  was not in the right state. Retry the hold sequence.
  (Helper: `tools\board-flashing\flash_b1_send.py`, plus
  `esp_bootmode.py` / `esp_boot_hold.py` / `esp_polarity_probe.py` /
  `esp_rom_banner.py` in the same folder were built to debug this exact issue.)
- **Board 3 (RX)**: does not need the BOOT button; plug in on COM4 and flash.

### 6.3 Capture (the M2 repro)
```powershell
cd <repo root>
python tools\csi_capture.py COM4 60 data\csi_run2_ht20_60hz.csv
```
- Optional startup delay parameter exists; see `tools/csi_capture.py --help`.

### 6.4 Analyze
```powershell
python tools\csi_analyze.py data\csi_run2_ht20_60hz.csv
```
Output includes: packet count, effective rate, delivery rate (assumed from
`CONFIG_SEND_FREQUENCY`), median/granularity/percentiles of the inter-packet
interval, and the interval histogram. Compare against `docs/m2-data-quality.md`.

## 7. Repository layout

```
.                     # repo root
  HANDOVER.md         # this file
  .gitignore          # ignores firmware/esp-csi, build/, sdkconfig.old, documents/*.pdf
  data/
    csi_run1.csv            # HT40  benchmark capture (Run 1)
    csi_run2_ht20_60hz.csv  # HT20  baseline capture (Run 2)
  docs/
    m2-data-quality.md      # M2 report + decision (HT20 @ 60 pkt/s)
  documents/          # *.pdf proposals / research; NOT committed by default
  firmware/
    esp-csi/          # external clone (github.com/espressif/esp-csi); NOT committed
  hardware/
    board-inventory.md          # measured board table + risk log H-01..H-10
    board-flashing/             # BOOT-button probes & helpers (see tools/ too)
  tools/
    csi_capture.py        # serial → CSV capture
    csi_analyze.py        # CSV → data-quality report
    board-flashing/
      esp_bootmode.py
      esp_boot_hold.py
      esp_polarity_probe.py
      esp_rom_banner.py
      flash_b1_send.py
```

Note: `hardware/board-flashing/` also appears in the tree (joined with `tools/`
for the flashing helpers); it contains the 5 verified helper scripts named above,
so the clickable path is `tools\board-flashing\` in this repository.

## 8. Risks (from hardware inventory, condensed)

| ID  | Risk | Mitigation |
|-----|------|------------|
| H-01 | Proposal assumed 3x ESP32-S3; we actually have 2x ESP32 + 1x ESP8266 | Use `idf.py set-target esp32`; classify ESP8266 as TX-only/spare |
| H-02 | Board 1 needs BOOT-button hold to enter download mode | Documented procedure + `flash_b1_send.py` helper |
| H-03 | All configured/serial links hang off COM4 | Use only one board at a time on COM4; write a COM-lane map in M3 |
| H-04 | 4 MB flash is a tight budget for larger CSI apps | Prepared vendor-nodes; lower OTA/asset goals if needed |
| H-05 | MAC `ec:64:c9:7b:0b:a0` differs from proposal's assumed Skylake-era MACs | Logging layer uses burned MAC as identity |
| H-06 | ESP8266 not CSI-capable | Flagged in M0 and removed from CSI path |
| H-07 | Room geometry assumptions untested | Riskcs are M3-P4; leave geometry to a labelled experiment |
| H-08 | ESP-IDF v5.4.4 is a specific, non-portable local install | Pin the exact version in HANDOVER (this file) and project docs |
| H-09 | CP2102 ↔ UART20 is a serial bottleneck (Run 1 jitter/loss) | Made `sys_config` simpler and dropped to HT20 @ 60 pkt/s |
| H-10 | First CSI frame after `esp_wifi_set_csi(true)` is `first_word_invalid` | Capture script should ignore/discard the very first CSI word; revisit in M3-P2 |

Not every risk detail is repeated here; the longer-form table lives in
`hardware/board-inventory.md`.

## 9. M3 — in progress (M3-P1 build-verified, awaiting hardware validation)

Goal from the friend-side brief: move from raw captures to labelled, classifiable
data. Five planned work packages:

1. **M3-P1 — UDP transport** (replaces USB-serial): reduces the CP2102↔UART
   ceiling (H-09) that limits CSI-rate headroom. IMPLEMENTED and build-verified:
   `csi_recv` now sends each `CSI_DATA,…` line over UDP from `wifi_csi_rx_cb`
   (after the MAC filter / gain block), and `tools/udp_listener.py` receives it
   into the same CSV format as `tools/csi_capture.py`, so `tools/csi_analyze.py`
   works unchanged.
   - Build both images: `csi_recv` (edited) + `csi_send` (unchanged).
   - Configure `csi_recv/main/app_main.c`: set `CONFIG_CSI_UDP_SSID`,
     `CONFIG_CSI_UDP_PASSWORD` (AP on **channel 11**, to match ESP-NOW/CSI), and
     `CONFIG_CSI_UDP_TARGET_IP` (the PC's IP), port `9000`.
   - Flash Board 3 (RX) with `csi_recv.bin`; flash Board 1 (TX) with
     `csi_send.bin`.
   - Run: `python tools\udp_listener.py 9000 60 data\csi_udp_ht20_60hz.csv`
   - Validate vs M2 Run 2 baseline (HT20 @ 60 pkt/s): target ~58.5 pkt/s,
     delivery ≥99%, interval jitter σ ~1.65 ms. Compare with
     `tools\csi_analyze.py` and `docs\m2-data-quality.md`.
   - Caveat: RX runs promiscuous mode + STA backhaul on ch 11. If CSI drops,
     revisit (e.g., drop promiscuous or dedicate the channel).
2. **M3-P2 — first-word correction**: confirm / clean the `first_word_invalid`
   (H-10) artifact; decide whether to drop the first CSI word or rework the
   capture script's init sequence.
3. **M3-P3 — HT20 vs HT40 comparison** (already partially resolved by M2
   baseline, but keep a scripted A/B in case a future protocol needs HT40).
4. **M3-P4 — TX/RX geometry**: a labelled experiment with positions relevant to
   the desired sensing application (hand-wave, walk-through, still-present).
   This is where the "purchased" third node (§10) becomes useful.
5. **M3-P5 — capture metadata**: enrich each CSV row with the extra fields the
   labeling work will need (timestamp, TX/RX MAC, room ID, session ID, gain).

### Definite next steps (in order)
- (a) Flash Board 3 (RX) with the new `csi_recv.bin` and Board 1 (TX) with
  `csi_send.bin`; configure the AP to channel 11 and set the SSID/password/IP in
  `csi_recv/main/app_main.c`, then validate UDP throughput vs the Run 2 baseline
  (~58.5 pkt/s, ≥99% delivery, jitter σ ~1.65 ms).
- (b) Pull in a labelled-capture plan if a third node can be obtained —
  otherwise start on M3-P4 geometry with the existing 2 nodes.
- (c) Prepare an M3 data-quality report similar in shape to M2's, so the
  baseline can be compared fairly across hardware variants.

## 10. Hardware purchase recommendation

- **Recommended**: 1x additional ESP32 **classic** (not S3, not ESP8266).
  Reason: the 2 nodes already installed use classic ESP32; mixing S3/D0WD
  families in the same CSI mesh complicates calibration and rate mapping,
  and ESP8266 is excluded (H-06).
- **Also useful (2nd purchase)**: another CP2102-compatible USB↔UART bridge
  (or a board that already integrates one) so the third node can occupy a
  COM port **other than COM4** — this avoids the COM4 contention risk (H-03).
- The ESP8266 (Board 2) is not worth buying more of for this project.
- Optional future investment, not required for M3: a second CP2102 with
  ≥2 ports (e.g., CH340-based 4-port) to run several CSI nodes without unplug cycles.

## 11. Open questions to ask the friend

1. Does the friend's PC already have `author / E:\Espressif\isp-idf` set up, or
   should we ship a dollar-free `requirements.txt` / `idf_setup.ps1`?
2. Should commits be pushed to a git remote (GitHub/GitLab)? At the time of
   writing nothing has been pushed; `master` has only the initial local commit.
3. Are the `documents/*.pdf` files third-party and should they stay prevented
   from being committed (`documents/*.pdf` in `.gitignore`), or should a
   subset be checked in locally only (without sharing)?
4. For M3-P4 (geometry), does the preferred room have attic-like obstructions
   (people, parked equipment) that will act as hard reflectors?

---

*Handover written based on work in the M0–M2 milestone window. Please read
`docs/m2-data-quality.md` and `hardware/board-inventory.md` for the two
context documents that shaped the M2 baseline and the risk list.*
