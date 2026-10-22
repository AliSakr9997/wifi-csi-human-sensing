import serial, time, esptool

PORT = "COM4"
print("Pulsing EN every 2s for ~30s. HOLD BOOT until I say release.\n")

result = None
for i in range(15):
    try:
        ser = serial.Serial()
        ser.port = PORT
        ser.baudrate = 115200
        ser.timeout = 0.15
        ser.dtr = False
        ser.rts = False
        ser.open()
        time.sleep(0.1)
        # pulse EN (reset) -> chip samples IO0 (BOOT held => LOW) => download
        ser.rts = True
        time.sleep(0.15)
        ser.rts = False
        time.sleep(0.15)
        n = ser.in_waiting
        bl = ser.read(n) if n else b""

        esp = esptool.ESP32ROM(port=ser, baud=115200)
        try:
            esp.connect(mode="no-reset", attempts=1, warnings=False)
            result = esp
            print(f"[{i}] SYNC OK  bootlog={bl[:120]!r}")
            break
        except Exception as e:
            print(f"[{i}] no sync ({str(e)[:45]})  bootlog={bl[:90]!r}")
            try:
                esp._port.close()
            except Exception:
                pass
    except Exception as e:
        print(f"[{i}] port err: {e}")
    time.sleep(1.5)

print("\n" + "=" * 50)
if result is not None:
    print("CONNECTED")
    for label, fn in [
        ("chip", lambda: result.get_chip_description()),
        ("features", lambda: getattr(result, "get_chip_features", lambda: "?")()),
        ("mac", lambda: ":".join("%02x" % b for b in result.read_mac())),
    ]:
        try:
            print(f"  {label}: {fn()}")
        except Exception as e:
            print(f"  {label}: ERR {e}")
    try:
        import esptool
        print("  flash:", esptool.detect_flash_size(result))
    except Exception as e:
        print("  flash: ERR", e)
else:
    print("STILL NO SYNC")
