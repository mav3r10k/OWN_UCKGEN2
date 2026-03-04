#!/usr/bin/env python3
# ============================================================
#  UCK-G2 Custom Display Daemon
#  Framebuffer: /dev/fb0 — 160x60px — 16bpp RGB565 — 180° rot
#  Ersetzt ck-ui und zeigt System/Docker-Status
#  Abhängigkeiten: pillow  →  pip3 install pillow --break-system-packages
# ============================================================

import os, time, socket, subprocess, sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Fehlt: pillow  →  pip3 install pillow --break-system-packages")
    sys.exit(1)

# ── Konstanten ───────────────────────────────────────────────
FB_DEV   = "/dev/fb0"
FB_W     = 160
FB_H     = 60
ROTATE   = 180      # Display ist 180° montiert
INTERVAL = 5        # Aktualisierungsintervall in Sekunden

# Farben (RGB)
BLACK  = (  0,   0,   0)
WHITE  = (255, 255, 255)
BLUE   = ( 82, 148, 255)
GREEN  = ( 80, 210, 120)
YELLOW = (255, 200,   0)
RED    = (255,  80,  80)
GRAY   = (110, 110, 110)
DKBLUE = ( 20,  40,  80)

# ── RGB888 → RGB565 (16bpp, Little Endian) ───────────────────
def rgb888_to_rgb565(img: Image.Image) -> bytes:
    """Konvertiert PIL-Image (RGB) → bytearray im RGB565-Format"""
    pixels = img.load()
    buf = bytearray(FB_W * FB_H * 2)
    idx = 0
    for y in range(FB_H):
        for x in range(FB_W):
            r, g, b = pixels[x, y]
            pixel = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf[idx]     = pixel & 0xFF
            buf[idx + 1] = (pixel >> 8) & 0xFF
            idx += 2
    return bytes(buf)

# ── System-Infos ─────────────────────────────────────────────
def get_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "kein Netz"

def get_ram() -> tuple[int, int]:
    """Gibt (used_MB, total_MB) zurück"""
    try:
        out = subprocess.check_output(
            "free -m | awk 'NR==2{print $2,$3}'",
            shell=True, timeout=2).decode().strip().split()
        return int(out[1]), int(out[0])
    except:
        return 0, 0

def get_temp() -> float:
    try:
        for zone in range(5):
            p = f"/sys/class/thermal/thermal_zone{zone}/temp"
            if os.path.exists(p):
                return int(open(p).read().strip()) / 1000.0
    except:
        pass
    return 0.0

def get_docker() -> tuple[int, int]:
    """Gibt (running, total) Container zurück"""
    try:
        running = int(subprocess.check_output(
            "docker ps -q 2>/dev/null | wc -l",
            shell=True, timeout=2).decode().strip())
        total = int(subprocess.check_output(
            "docker ps -aq 2>/dev/null | wc -l",
            shell=True, timeout=2).decode().strip())
        return running, total
    except:
        return -1, -1

def get_uptime() -> str:
    try:
        secs = float(open("/proc/uptime").read().split()[0])
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h{m:02d}m"
    except:
        return ""

# ── Display-Helligkeit setzen ────────────────────────────────
def set_brightness(value: int = 15):
    try:
        with open("/sys/class/backlight/fb_sp8110/brightness", "w") as f:
            f.write(str(value))
    except:
        pass

# ── Einen Frame zeichnen ─────────────────────────────────────
def draw_frame() -> Image.Image:
    img  = Image.new("RGB", (FB_W, FB_H), BLACK)
    draw = ImageDraw.Draw(img)

    # Daten sammeln
    ip             = get_ip()
    ram_used, ram_total = get_ram()
    temp           = get_temp()
    docker_run, docker_total = get_docker()
    uptime         = get_uptime()
    zeit           = time.strftime("%H:%M")

    # RAM-Auslastung in %
    ram_pct = int(ram_used / ram_total * 100) if ram_total else 0
    ram_color = GREEN if ram_pct < 70 else YELLOW if ram_pct < 85 else RED

    # Temperatur-Farbe
    temp_color = GREEN if temp < 60 else YELLOW if temp < 75 else RED

    # Docker-Farbe
    if docker_run < 0:
        docker_str   = "n/a"
        docker_color = GRAY
    else:
        docker_str   = f"{docker_run}/{docker_total}"
        docker_color = GREEN if docker_run > 0 else WHITE

    # ── Layout: 3 Zeilen + Kopfzeile ────────────────────────
    #  Y=0..11  → Header-Bar (blau)
    #  Y=13..23 → Zeile 1
    #  Y=25..35 → Zeile 2
    #  Y=37..47 → Zeile 3
    #  Y=50..59 → Footer

    # Header
    draw.rectangle([(0, 0), (FB_W, 11)], fill=DKBLUE)
    draw.text(( 3, 1), "UCK-G2",        fill=BLUE)
    draw.text((FB_W - 30, 1), zeit,     fill=WHITE)
    draw.text((68, 1), f"up {uptime}",  fill=GRAY)

    # Zeile 1: IP
    draw.text((2, 14), "IP",            fill=GRAY)
    draw.text((22, 14), ip,             fill=WHITE)

    # Zeile 2: RAM + Temp
    draw.text((2, 26), "RAM",           fill=GRAY)
    draw.text((22, 26), f"{ram_used}/{ram_total}MB ({ram_pct}%)", fill=ram_color)

    # Trennpunkt
    draw.text((100, 26), "T",           fill=GRAY)
    draw.text((110, 26), f"{temp:.0f}C", fill=temp_color)

    # Zeile 3: Docker
    draw.text((2, 38), "Docker",        fill=GRAY)
    draw.text((42, 38), docker_str,     fill=docker_color)
    if docker_run > 0:
        draw.text((60, 38), "aktiv",    fill=GREEN)

    # RAM-Balken unten
    bar_w = int((FB_W - 4) * ram_pct / 100)
    draw.rectangle([(2, 52), (FB_W - 2, 57)], fill=(30, 30, 50))
    draw.rectangle([(2, 52), (2 + bar_w, 57)], fill=ram_color)

    # 180° drehen (Display ist kopfüber montiert)
    img = img.rotate(ROTATE)
    return img

# ── Hauptloop ────────────────────────────────────────────────
def main():
    print(f"UCK-G2 Display Daemon gestartet")
    print(f"Framebuffer: {FB_W}x{FB_H}px @ 16bpp RGB565, {ROTATE}° Rotation")
    print(f"Gerät: {FB_DEV}  |  Intervall: {INTERVAL}s")

    set_brightness(15)

    try:
        fb = open(FB_DEV, "wb")
    except PermissionError:
        print(f"Kein Zugriff auf {FB_DEV} — als root ausführen!")
        sys.exit(1)
    except FileNotFoundError:
        print(f"{FB_DEV} nicht gefunden!")
        sys.exit(1)

    print("Display aktiv — Ctrl+C zum Beenden")

    while True:
        try:
            frame = draw_frame()
            raw   = rgb888_to_rgb565(frame)
            fb.seek(0)
            fb.write(raw)
            fb.flush()
        except KeyboardInterrupt:
            print("\nBeendet.")
            break
        except Exception as e:
            print(f"Frame-Fehler: {e}", flush=True)
        time.sleep(INTERVAL)

    fb.close()
    # Display schwärzen beim Beenden
    try:
        with open(FB_DEV, "wb") as fb:
            fb.write(bytes(FB_W * FB_H * 2))
    except:
        pass

if __name__ == "__main__":
    main()
