import serial, time, subprocess, sys, os
import esptool

PORT = "COM5"
PROJ = r"E:\Vli\PROJECTS\Project 2 - wifi sensing\firmware\esp-csi\examples\get-started\csi_send"

print(">>> HOLD the BOOT button on Board 1 down and KEEP it held.", flush=True)
print(">>> Entering download mode (retry loop, up to ~40s)...", flush=True)

esp = None
for i in range(40):
    try:
        ser = serial.Serial()
        ser.port = PORT
        ser.baudrate = 115200
        ser.timeout = 0.15
        ser.dtr = False
        ser.rts = False
        ser.open()
        time.sleep(0.08)
        ser.rts = True
        time.sleep(0.12)
        ser.rts = False
        time.sleep(0.12)
        rom = esptool.ESP32ROM(port=ser, baud=115200)
        try:
            rom.connect(mode="no-reset", attempts=1, warnings=False)
            esp = rom
            print(f"[{i}] SYNC OK -> download mode", flush=True)
            break
        except Exception as ex:
            try:
                rom._port.close()
            except Exception:
                pass
            print(f"[{i}] no sync ({str(ex)[:45]})", flush=True)
    except Exception as ex:
        print(f"[{i}] port err {ex}", flush=True)
    time.sleep(0.5)

if esp is None:
    print("NEVER ENTERED DOWNLOAD MODE - is BOOT being held down?", flush=True)
    sys.exit(2)

try:
    esp._port.close()
except Exception:
    pass
time.sleep(0.2)

print(">>> Download mode confirmed. Flashing csi_send (keep holding BOOT)...", flush=True)
args = [
    sys.executable, "-m", "esptool",
    "--chip", "esp32", "-p", PORT,
    "--before", "no-reset", "--after", "hard-reset",
    "-b", "460800",
    "write-flash", "--flash-mode", "dio", "--flash-freq", "40m", "--flash-size", "2MB",
    "0x1000", os.path.join(PROJ, "build", "bootloader", "bootloader.bin"),
    "0xa000", os.path.join(PROJ, "build", "partition_table", "partition-table.bin"),
    "0x20000", os.path.join(PROJ, "build", "csi_send.bin"),
]
sys.exit(subprocess.run(args).returncode)
