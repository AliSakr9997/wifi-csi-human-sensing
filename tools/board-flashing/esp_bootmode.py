import serial, time, subprocess, sys

PORT = "COM4"

def esptool_connect(before):
    p = subprocess.run(
        [sys.executable, "-m", "esptool", "-p", PORT, "--before", before,
         "--after", "hard-reset", "--connect-attempts", "3", "chip-id"],
        capture_output=True, text=True, timeout=90,
    )
    return (p.stdout or "") + (p.stderr or "")

# Attempt 1: plain esptool retry (its own auto-reset)
print("### ATTEMPT 1: esptool default auto-reset ###")
out = esptool_connect("default-reset")
print(out.strip()[-700:])
if "Chip is" in out or "Chip is ESP32" in out or "Detecting chip type" in out:
    print(">>> AUTO-RESET WORKS")
    sys.exit(0)

# Attempt 2: manual DTR/RTS dance (esptool polarity), then no-reset
print("\n### ATTEMPT 2: software DTR/RTS dance -> esptool --before no-reset ###")
s = serial.Serial(PORT, 115200, timeout=0.2)
s.dtr = False; s.rts = False; time.sleep(0.1)
s.rts = True;  time.sleep(0.15)     # EN low (reset)
s.dtr = True;  time.sleep(0.15)     # IO0 low (download)
s.rts = False; time.sleep(0.1)      # EN high -> boot into download
# leave IO0 low, keep port open while esptool runs is not possible; close and hope lines hold
s.close()
out = esptool_connect("no-reset")
print(out.strip()[-700:])
if "Chip is" in out or "Detecting chip type" in out:
    print(">>> SOFTWARE DANCE WORKS")
    sys.exit(0)

print("\n>>> NEITHER WORKED")
