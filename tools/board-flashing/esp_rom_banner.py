import sys, time, serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM4"

def read_for(ser, secs, label):
    end = time.time() + secs
    buf = b""
    while time.time() < end:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
        else:
            time.sleep(0.02)
    text = buf.decode("utf-8", errors="replace")
    print(f"----- {label} ({len(buf)} bytes) -----")
    print(text if text.strip() else "<no data>")
    return buf

ser = serial.Serial()
ser.port = port
ser.baudrate = 115200
ser.timeout = 0.1
ser.dtr = False
ser.rts = False
ser.open()
time.sleep(0.3)

read_for(ser, 1.0, "passive (no reset)")

# classic ESP auto-reset circuit: RTS drives EN (active low)
ser.rts = True
time.sleep(0.15)
ser.rts = False
time.sleep(0.05)

read_for(ser, 3.0, "after reset pulse")

ser.close()
