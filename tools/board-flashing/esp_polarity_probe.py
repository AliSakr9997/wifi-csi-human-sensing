import serial, time

PORT = "COM4"

def run(seq):
    ser = serial.Serial()
    ser.port = PORT
    ser.baudrate = 115200
    ser.timeout = 0.2
    ser.dtr = False
    ser.rts = False
    ser.open()
    time.sleep(0.1)
    for act in seq:
        kind = act[0]
        if kind == "D":
            ser.dtr = bool(act[1])
        elif kind == "R":
            ser.rts = bool(act[1])
        elif kind == "W":
            time.sleep(act[1])
    time.sleep(0.2)
    n = ser.in_waiting
    bl = ser.read(n) if n else b""
    ser.close()
    mode = "?"
    if b"boot:0x3" in bl:
        mode = "DOWNLOAD(0x3)  <-- software reset works with this polarity"
    elif b"boot:0x13" in bl:
        mode = "flash-boot(0x13)"
    return mode, bl[:160]

seqs = {
    "A  R1 W.15 D1 W.05 R0   (EN-reset; IO0<-DTR=1)": [("R",1),("W",0.15),("D",1),("W",0.05),("R",0),("W",0.15)],
    "B  R1 W.15 D0 W.05 R0   (EN-reset; IO0<-DTR=0)": [("R",1),("W",0.15),("D",0),("W",0.05),("R",0),("W",0.15)],
    "C  D1 W.05 R1 W.15 R0   (IO0<-DTR=1 before reset)": [("D",1),("W",0.05),("R",1),("W",0.15),("R",0),("W",0.15)],
    "D  D0 W.05 R1 W.15 R0   (IO0<-DTR=0 before reset)": [("D",0),("W",0.05),("R",1),("W",0.15),("R",0),("W",0.15)],
    "E  D1 W.05 R0 W.15 D0   (swapped: EN<-DTR?)": [("D",1),("W",0.05),("R",0),("W",0.15),("D",0),("W",0.15)],
    "F  R0 W.05 R1 W.15 R0   (EN pulse only)": [("R",0),("W",0.05),("R",1),("W",0.15),("R",0),("W",0.15)],
}

for name, seq in seqs.items():
    mode, bl = run(seq)
    print(f"{name}\n     -> {mode}")
    print(f"        raw: {bl!r}\n")
