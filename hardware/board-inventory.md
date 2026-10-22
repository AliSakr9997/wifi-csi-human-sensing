# Hardware Board Inventory — Wi-Fi CSI Project

**Owner:** Embedded & CSI Engineer
**Last updated:** 2026-10-18
**Purpose:** Canonical record of every board in the project, its exact identity, how it
was verified, and any hardware constraints that affect flashing, CSI capture, and
reproducibility.

> Legend for **Status**: ✅ verified on our hardware · ⏳ pending · 📄 from documentation/datasheet

---

## 1. Summary table

| # | Chip / module | Revision | Flash | Crystal | MAC | USB bridge | Host port | Download mode | CSI usable? | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ESP32-D0WD-V3 (WROOM-32 class) | v3.1 | 4 MB | 40 MHz | `ec:64:c9:7b:0b:a0` | CP2102 | COM4 | **BOOT button only** | ✅ yes (ESP32) | ✅ |
| 2 | **ESP8266EX** | — | 4 MB | 26 MHz | `2c:f4:32:18:fd:b3` | CP2102 | COM4 | automatic | ❌ **no** (ESP8266) | ✅ |
| 3 | ESP32-D0WD-V3 (WROOM-32 class) | v3.1 | 4 MB | 40 MHz | `28:56:2f:49:59:58` | CP2102 | COM4 | automatic | ✅ yes (ESP32) | ✅ |

### 1.1 Node availability (the important consequence)
| Role | Boards available | Notes |
|---|---|---|
| CSI-capable (ESP32) | **2** — Board 1, Board 3 | both classic ESP32-D0WD-V3, rev v3.1 |
| CSI-incapable | 1 — Board 2 | ESP8266EX; can't run esp-csi |
| Proposal assumed | 3× **ESP32-S3**-DevKitC-1 | ❌ not what we have |

> **Reality vs. plan:** the project assumed 3 ESP32 modules for the CSI mesh, but the
> hardware on hand is **2× classic ESP32 + 1× ESP8266**. That means:
> - at most **2 nodes** for CSI (e.g. 1× TX + 1× RX, or 2× RX);
> - the ESP8266 can only be a plain Wi-Fi transmitter (not a receiver) if we deliberately use it as CSI-TX;
> - the design must target `esp32` (not `esp32s3`) in ESP-IDF, and the "3-node mesh" in the proposal needs re-scoping or extra hardware.

---

## 2. Board 1 — ESP32-D0WD-V3

### 2.1 Identity (verified)
| Field | Value |
|---|---|
| Chip | `ESP32-D0WD-V3` |
| Chip revision | `v3.1` |
| Chip family | Classic ESP32 (not S2/S3/C3) |
| Features | Wi-Fi, BT, Dual Core + LP Core, 240 MHz, Vref calibration in eFuse, Coding Scheme: None |
| Crystal | 40 MHz |
| Flash size | **4 MB** |
| Flash manufacturer ID | `0x85` (likely Puya) |
| Flash device ID | `2016` |
| Flash voltage | 3.3 V (set by strapping pin) |
| MAC (STA base) | `ec:64:c9:7b:0b:a0` |
| Module class | ESP32-WROOM-32 / -32E class (single 2.4 GHz radio) |

### 2.2 Connection (verified)
| Field | Value |
|---|---|
| USB connector on board | Single **Micro-USB** |
| USB-to-UART bridge | **CP2102** (Silicon Labs) |
| USB VID:PID | `10C4:EA60` |
| Host serial port | **COM4** (Windows 11) |
| Driver required | Silicon Labs CP210x VCP, **v11.5.0.417** |
| Driver source | Microsoft Update Catalog (signed) — published as `oem64.inf` |

### 2.3 Boot / flashing behaviour (verified)
| Field | Value |
|---|---|
| ROM bootloader banner | `ets Jul 29 2019 12:21:46` (original ESP32 ROM) |
| Default boot mode | `boot:0x13 (SPI_FAST_FLASH_BOOT)` |
| Download boot mode | `boot:0x3 (DOWNLOAD_BOOT(UART0/UART1/SDIO_REI_REO_V2))` + `waiting for download` |
| Auto-reset (esptool) | ❌ **Does NOT work** — `Wrong boot mode detected (0x13)` |
| DTR → GPIO0 (IO0) | ❌ **Not wired.** All DTR polarities still yield `boot:0x13` |
| RTS → EN | ✅ Works (RTS pulse resets the chip) |
| **Required flashing procedure** | **Hold `BOOT`, then pulse reset (or tap `EN`), then release `BOOT`.** |

**Consequence for the workflow:** every `idf.py flash` / `esptool` write must be
preceded by manually holding `BOOT`. There is no software-only path. A jumper from
`IO0` to `GND` is an equivalent alternative.

### 2.4 Firmware currently on the board (verified)
Board 1 is **not** blank. It runs an unrelated program:
```
===== GPS SERIAL OUTPUT MODE =====
Waiting for GPS fix...
```
Unrelated to our project and **safe to overwrite** in Milestone 1.

### 2.5 CSI suitability
✅ **Verified role: ESP-NOW transmitter.** Board 1 runs `csi_send` (sets its STA MAC to
`1a:00:00:00:00:00`, channel 11, HT40, ~100 packets/s). It logs only at boot
(`================ CSI SEND ================`), then transmits silently.

---

## 3. Board 2 — ESP8266EX  ⚠️ NOT AN ESP32

### 3.1 Identity (verified)
| Field | Value |
|---|---|
| Chip | `ESP8266EX` |
| Chip ID | `0x0018fdb3` |
| Features | Wi-Fi, 160 MHz |
| Crystal | 26 MHz |
| Flash size | **4 MB** |
| Flash manufacturer ID | `0x20` (XMC) |
| Flash device ID | `4016` |
| MAC | `2c:f4:32:18:fd:b3` |
| ROM bootloader banner | `ets Jan  8 2013,rst cause:2, boot mode:(3,7)` **at 74880 baud** |

### 3.2 Connection (verified)
| Field | Value |
|---|---|
| USB-to-UART bridge | **CP2102** (Silicon Labs) — identical VID:PID to Boards 1 & 3 |
| USB VID:PID | `10C4:EA60` |
| Reported serial | `0001` (clone default → Windows reuses the same port) |
| Host serial port | **COM4** — **shared with Boards 1 & 3** |
| Driver | same CP210x VCP v11.5.0.417 |

> **Port-collision caveat:** all three CP2102s report serial `0001`, so Windows assigns
> the **same COM port and instance ID**. **Plug in only one board at a time**, or they
> are indistinguishable by port. (Distinguish by chip banner.)

### 3.3 Boot / flashing behaviour (verified)
| Field | Value |
|---|---|
| Auto-reset (esptool default-reset) | ✅ **Works** — no manual button needed |
| Download mode | automatic via DTR/RTS |
| ROM log baud | 74880 (ESP8266 standard) |

### 3.4 CSI suitability — ❌ NOT USABLE as a receiver
- Official `esp-csi` supports **ESP32 series only**: ESP32 / S2 / C3 / S3 / C5 / C6 / C61. **ESP8266 is not listed.**
- ESP-IDF does **not** support ESP8266 at all (legacy NONOS / ESP8266_RTOS SDK only).
- The ESP8266 NONOS SDK **API guide exposes no CSI function** — only promiscuous/sniffer APIs giving `rx_ctrl`/RSSI, not full CSI. (Espressif forum requests for ESP8266 CSI were never fulfilled.)
- **Conclusion:** Board 2 cannot receive CSI or run our ESP-IDF firmware. Reusable only as a plain Wi-Fi transmitter (CSI-TX) if we explicitly choose a non-ESP32 TX.

**Sources:**
- esp-csi README (family support list): https://github.com/espressif/esp-csi
- ESP8266 NONOS SDK API Guide (no CSI API): https://www.espressif.com/sites/default/files/2c-esp8266_non_os_sdk_api_guide_en_v1.5.4.pdf

---

## 4. Board 3 — ESP32-D0WD-V3

### 4.1 Identity (verified)
| Field | Value |
|---|---|
| Chip | `ESP32-D0WD-V3` |
| Chip revision | `v3.1` |
| Chip family | Classic ESP32 (not S2/S3/C3) — same class as Board 1 |
| Features | Wi-Fi, BT, Dual Core + LP Core, 240 MHz, Vref calibration in eFuse, Coding Scheme: None |
| Crystal | 40 MHz |
| Flash size | **4 MB** |
| Flash manufacturer ID | `0x68` (Boya) |
| Flash device ID | `4016` |
| Flash voltage | 3.3 V (set by strapping pin) |
| MAC (STA base) | `28:56:2f:49:59:58` |
| Module class | ESP32-WROOM-32 / -32E class (single 2.4 GHz radio) |

### 4.2 Connection (verified)
| Field | Value |
|---|---|
| USB-to-UART bridge | **CP2102** (Silicon Labs) |
| USB VID:PID | `10C4:EA60` |
| Reported serial | `0001` (shares port/instance with Boards 1 & 2) |
| Host serial port | **COM4** |

### 4.3 Boot / flashing behaviour (verified)
| Field | Value |
|---|---|
| ROM bootloader banner | `ets Jul 29 2019 12:21:46` (original ESP32 ROM) |
| Default boot mode | `boot:0x13 (SPI_FAST_FLASH_BOOT)` |
| Auto-reset (esptool) | ✅ **WORKS** — connected with no manual button |
| **Flashing note** | Unlike Board 1, this board flashes automatically (DTR/RTS wired correctly) → **use Board 3 as the primary flashing/test board.** |

### 4.4 Firmware currently on the board (verified)
Board 3 is **not** blank. It runs an unrelated program whose serial output is:
```
ets Jul 29 2019 12:21:46
rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
mode:DIO, clock div:1
entry 0x400805f0
Failed to find MPU6050 chip!
```
Looks like an **MPU6050 IMU demo**. Unrelated to our project and **safe to overwrite**.

### 4.5 CSI suitability
✅ **Verified role: CSI receiver.** Board 3 runs `csi_recv` and captured **4197 CSI
packets in 60 s** (~70 packets/s after some serial loss), RSSI ≈ −59…−62 dBm, channel 11,
`sig_mode=1` (HT), 384 int8 samples per packet (192 I/Q pairs). Sample CSV:
`data/csi_run1.csv`.

---

## 5. Host / toolchain environment (verified)

| Item | Value |
|---|---|
| OS | Windows 11 Home, build `10.0.26200` (25H2) |
| Python | 3.12.5 |
| esptool | `5.6.0` (installed via pip) |
| PySerial | 3.5 |
| Data libs present | numpy 1.26.4, scipy 1.14.1, pandas 2.2.3, matplotlib 3.9.2 |
| ESP-IDF | ✅ **v5.4.4** — `E:\Espressif\esp-idf` (clone), target **`esp32`** |
| IDF tools / Python env | `E:\Espressif\` (`IDF_TOOLS_PATH`): xtensa-esp-elf, cmake, ninja, ccache, openocd-esp32, xtensa gdb, python_env |
| IDF entry command | `$env:IDF_TOOLS_PATH='E:\Espressif'; cmd /c "call E:\Espressif\esp-idf\export.bat && idf.py …"` |
| Arduino IDE | 2.x installed (no ESP32 core installed) |
| VS Code | installed |

---

## 6. Reproduction procedure (used for Boards 1–3)

Run from Windows PowerShell.

1. **Detect the USB bridge**
   ```powershell
   Get-PnpDevice -Class Ports | Select-Object Status,FriendlyName,InstanceId
   Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_' } | Select-Object Name,InstanceId
   ```
   `VID_10C4` = CP210x, `VID_1A86` = CH34x, `VID_303A` = Espressif native USB.

2. **CP210x driver** (only if Code 28 / no COM port): Silicon Labs VCP installer, or
   Microsoft Update Catalog search `CP210x`. Installed here as v11.5.0.417.

3. **Read the ROM banner (no flashing)** — open the port and reset, then read:
   - classic ESP32 → `ets Jul 29 2019` @ **115200**
   - ESP8266 → `ets Jan  8 2013` @ **74880**  ← different baud!
   - ESP32-S3 → `ESP-ROM:esp32s3-…`; ESP32-C3 → `ESP-ROM:esp32c3-…`

4. **Definitive chip/flash ID via esptool:**
   ```powershell
   python -m esptool -p COM4 chip-id
   python -m esptool -p COM4 flash-id
   ```
   If a board has no working auto-reset (Board 1), first put it in download mode
   manually (hold `BOOT` → tap `EN`/`RST` → release `BOOT`) and add `--before no-reset`.

---

## 7. Known issues / risk log

| ID | Issue | Affects | Status |
|---|---|---|---|
| H-01 | Board 1 has no working auto-reset (DTR not wired to IO0) → manual BOOT for every flash | Embedded (M1), Experimentation | Open — use Board 3 for auto flashing |
| H-02 | Board 1 ships with unrelated GPS firmware | Embedded | Will be overwritten in M1 |
| H-03 | ESP-IDF not yet installed | Embedded, Signal Processing | ✅ **Resolved** — IDF v5.4.4 on `E:`, target `esp32` |
| H-04 | Boards 2 & 3 unidentified | Embedded, all downstream | ✅ **Resolved** — Board 2 = ESP8266, Board 3 = ESP32-D0WD-V3 |
| H-05 | Board 2 is an ESP8266 → cannot be a CSI receiver; unsupported by esp-csi/ESP-IDF | Embedded, AI/ML (dataset), Experimentation, Backend | Open — limits us to 2 CSI nodes |
| H-06 | All three CP2102 boards share COM4 / instance ID (serial `0001`) → one at a time | Embedded, Experimentation | Open — workaround documented |
| H-07 | Hardware is 2× classic ESP32 + 1× ESP8266, **not** the 3× ESP32-S3 the proposal assumes | Embedded, AI/ML, Experimentation, Backend | **Open — needs re-scoping or buying ESP32-S3 units** |
| H-08 | Boards 1 & 3 target `esp32` (classic), not `esp32s3` → FQBN/IDF target differs from proposal | Embedded | Open — set target `esp32` in ESP-IDF |
| H-09 | **UART link is a throughput ceiling:** ~1.32 KB/packet → ≈70 pkt/s at 921600 baud (classic CP2102 caps near 921600). Caused 23 % packet loss at HT40/100 pkt/s. | Embedded, Experimentation, AI/ML | Mitigated for M2 (HT20 @ 60 pkt/s → 99.4 % delivery). **M3 prerequisite: migrate transport to Wi-Fi/UDP** (`docs/m2-data-quality.md` §7, item M3-P1) |
| H-10 | `first_word_invalid = 1` on **every** CSI packet | AI/ML, Experimentation | Open — DSP must discard the first CSI word (see `docs/m2-data-quality.md` §5) |

---

## 8. Provenance
All values in Sections 2–4 were read directly from the physical boards
(ROM banner + `esptool v5.6.0` `chip-id` / `flash-id`). No value here is assumed
unless explicitly marked. All three boards have now been measured.

---

## 9. CSI pipeline status (M1 — verified 2026-10-18)

| Item | Value |
|---|---|
| Firmware | `esp-csi/examples/get-started/csi_send` (Board 1) + `csi_recv` (Board 3) |
| IDF / target | ESP-IDF **v5.4.4**, target **`esp32`** |
| Transport | ESP-NOW, channel **11**, sender MAC `1a:00:00:00:00:00` |
| Bandwidth / rate | **HT20** (128 subcarriers) @ **~60 pkt/s** — changed from HT40/100 pkt/s for a loss-free link |
| Sender console | 115200 (boot banner only) |
| Receiver console | **921600** (streams `CSI_DATA` lines) |
| Captures | `data/csi_run1.csv` (HT40@100/s, 76.9 % delivered) · `data/csi_run2_ht20_60hz.csv` (HT20@60/s, **99.4 % delivered**) |
| Logger / analyser | `tools/csi_capture.py`, `tools/csi_analyze.py` |
| Result | ✅ **First real CSI captured (M1)**; **M2 data-quality gate passed** — see `docs/m2-data-quality.md` |

**Board roles (fixed):** Board 3 = receiver (auto-reset, COM4) · Board 1 = transmitter
(manual BOOT, COM5). Both boards must be plugged into **different USB ports** to get
COM4 + COM5 simultaneously (see H-06).

**Flashing reminder:** Board 1 needs BOOT held to enter download mode. Working method:
a retry-loop that pulses RTS while BOOT is held, then `esptool --before no-reset`.
