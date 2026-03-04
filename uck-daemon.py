#!/usr/bin/env python3
# ============================================================
#  UCK-G2 Display + LED Daemon v3
#
#  Display: 3 rotierende Screens (160x60px, 16bpp, /dev/fb0)
#    Screen 1 → System-Status
#    Screen 2 → CPU / RAM / Disk Balken
#    Screen 3 → Netzwerk RX/TX
#
#  LEDs:
#    ulogo_ctrl → Heartbeat-Pulse (immer aktiv)
#    blue       → System-Status (OK=an, Last=blink, Docker=aus)
#    white      → Netzwerk-Aktivität (Helligkeit = Last)
#
#  Update:       alle 5 Sekunden
#  Screen-Wechsel: alle 2 Minuten mit Slide-Animation
# ============================================================

import os, time, socket, subprocess, sys, threading

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Fehlt: apt-get install -y python3-pil"); sys.exit(1)

# ── Konfiguration ────────────────────────────────────────────
FB_DEV       = "/dev/fb0"
FB_W         = 160
FB_H         = 60
ROTATE       = 0
UPDATE_SECS  = 5
SCREEN_SECS  = 120
NUM_SCREENS  = 3

# LED sysfs-Pfade
LED_BLUE     = "/sys/class/leds/blue/brightness"
LED_WHITE    = "/sys/class/leds/white/brightness"
LED_LOGO_PAT = "/sys/class/leds/ulogo_ctrl/pattern"
LED_LOGO_BRI = "/sys/class/leds/ulogo_ctrl/brightness"
LED_BLUE_TRG = "/sys/class/leds/blue/trigger"
LED_WHITE_TRG= "/sys/class/leds/white/trigger"

# Schwellwerte
THRESH_WARN  = 70   # % – gelbe Zone
THRESH_CRIT  = 85   # % – rote Zone / Blink

# Farben
BLACK  = (  0,   0,   0)
WHITE  = (255, 255, 255)
BLUE   = ( 82, 148, 255)
DKBLUE = ( 15,  35,  75)
GREEN  = ( 80, 210, 120)
YELLOW = (255, 200,   0)
RED    = (255,  80,  80)
GRAY   = (100, 100, 100)
CYAN   = (  0, 200, 220)
ORANGE = (255, 140,   0)

# ── LED-Steuerung ────────────────────────────────────────────
def led_write(path, value):
    try:
        with open(path, "w") as f:
            f.write(str(value))
    except:
        pass

def led_init():
    """Trigger auf none setzen für manuelle Kontrolle"""
    led_write(LED_BLUE_TRG,  "none")
    led_write(LED_WHITE_TRG, "none")
    led_write(LED_BLUE,  0)
    led_write(LED_WHITE, 0)
    led_write(LED_LOGO_PAT, "")

def led_logo_heartbeat():
    """Sanfter Heartbeat-Pulse für das Ubiquiti-Logo (läuft endlos)"""
    # Pattern: brightness duration_ms – zwei kurze Pulse wie Herzschlag
    # Puls 1: schnell hoch/runter, kurze Pause, Puls 2: hoch/runter, lange Pause
    pattern = "180 150 0 100 255 200 0 800"
    led_write(LED_LOGO_PAT, pattern)

def led_logo_alert():
    """Schnelles Blinken bei kritischem Zustand"""
    pattern = "255 100 0 100 255 100 0 100 255 100 0 500"
    led_write(LED_LOGO_PAT, pattern)

def led_logo_off():
    led_write(LED_LOGO_PAT, "")
    led_write(LED_LOGO_BRI, 0)

def led_set_status(ram_pct, cpu_pct, docker_run, docker_total):
    """
    Blue LED = System-Status:
      Docker OK + niedrige Last  → sanft leuchtend (200)
      Hohe Last (>THRESH_WARN)   → mittlere Helligkeit (120)
      Kritische Last (>THRESH_CRIT) → Pattern blinken
      Docker komplett down        → aus
    """
    max_load = max(ram_pct, cpu_pct)

    if docker_total > 0 and docker_run == 0:
        # Alle Container gestoppt
        led_write(LED_BLUE, 0)
        led_logo_alert()
    elif max_load >= THRESH_CRIT:
        # Kritische Last – Blink
        led_write(LED_BLUE, 255)
        led_logo_alert()
    elif max_load >= THRESH_WARN:
        # Erhöhte Last
        led_write(LED_BLUE, 120)
        led_logo_heartbeat()
    else:
        # Alles OK
        led_write(LED_BLUE, 200)
        led_logo_heartbeat()

def led_set_network(rx_rate, tx_rate):
    """
    White LED = Netzwerk-Last:
      Helligkeit proportional zur aktuellen Datenrate
      Basis: 10 Mbit/s = 1.25 MB/s → volle Helligkeit
    """
    total_rate = rx_rate + tx_rate
    # Skalierung: 0 bis 2.5 MB/s = 0 bis 255
    brightness = min(int(total_rate / 2_500_000 * 255), 255)
    # Mindesthelligkeit 15 wenn überhaupt Traffic
    if total_rate > 1000 and brightness < 15:
        brightness = 15
    led_write(LED_WHITE, brightness)

# ── RGB888 → RGB565 ──────────────────────────────────────────
def to_rgb565(img):
    pixels = img.load()
    buf = bytearray(FB_W * FB_H * 2)
    idx = 0
    for y in range(FB_H):
        for x in range(FB_W):
            r, g, b = pixels[x, y]
            p = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf[idx]     = p & 0xFF
            buf[idx + 1] = (p >> 8) & 0xFF
            idx += 2
    return bytes(buf)

# ── Zeichenhilfen ────────────────────────────────────────────
def heat_color(pct):
    if pct < THRESH_WARN:  return GREEN
    if pct < THRESH_CRIT:  return YELLOW
    return RED

def draw_bar(draw, x, y, w, h, pct, fg, bg=(20, 20, 40)):
    draw.rectangle([(x, y), (x+w, y+h)], fill=bg)
    filled = int(w * min(pct, 100) / 100)
    if filled > 0:
        draw.rectangle([(x, y), (x+filled, y+h)], fill=fg)

def draw_header(draw, title, screen_idx):
    draw.rectangle([(0, 0), (FB_W, 11)], fill=DKBLUE)
    draw.text((3, 1), title, fill=BLUE)
    for i in range(NUM_SCREENS):
        cx = FB_W - 7 - (NUM_SCREENS - 1 - i) * 7
        draw.ellipse([(cx-2, 3), (cx+2, 8)], fill=WHITE if i == screen_idx else GRAY)

# ── Daten sammeln ────────────────────────────────────────────
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3); s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except: return "kein Netz"

def get_ram():
    try:
        out = subprocess.check_output(
            "free -m | awk 'NR==2{print $2,$3}'",
            shell=True, timeout=2).decode().split()
        total, used = int(out[0]), int(out[1])
        return used, total, int(used * 100 / total)
    except: return 0, 0, 0

def get_cpu_pct():
    def stat():
        v = list(map(int, open("/proc/stat").readline().split()[1:]))
        return v[3], sum(v)
    try:
        i1, t1 = stat(); time.sleep(0.25); i2, t2 = stat()
        dt = t2 - t1
        return int((1 - (i2-i1)/dt) * 100) if dt else 0
    except: return 0

def get_temp():
    for z in range(5):
        p = f"/sys/class/thermal/thermal_zone{z}/temp"
        if os.path.exists(p):
            try: return int(open(p).read().strip()) / 1000.0
            except: pass
    return 0.0

def get_docker():
    try:
        r = int(subprocess.check_output("docker ps -q 2>/dev/null | wc -l",  shell=True, timeout=2).decode().strip())
        t = int(subprocess.check_output("docker ps -aq 2>/dev/null | wc -l", shell=True, timeout=2).decode().strip())
        return r, t
    except: return -1, -1

def get_disk():
    try:
        out = subprocess.check_output(
            "df -BG /srv | awk 'NR==2{print $2,$3,$5}'",
            shell=True, timeout=2).decode().strip().split()
        return int(out[1].rstrip('G')), int(out[0].rstrip('G')), int(out[2].rstrip('%'))
    except: return 0, 0, 0

def get_net_bytes(iface="eth0"):
    try:
        for line in open("/proc/net/dev"):
            if iface in line:
                p = line.split()
                return int(p[1]), int(p[9])
    except: pass
    return 0, 0

def fmt_rate(b):
    if b >= 1_000_000: return f"{b/1_000_000:.1f}MB/s"
    if b >= 1_000:     return f"{b/1_000:.0f}KB/s"
    return f"{b}B/s"

def fmt_total(b):
    if b >= 1_073_741_824: return f"{b/1_073_741_824:.1f}GB"
    if b >= 1_048_576:     return f"{b/1_048_576:.0f}MB"
    return f"{b//1024}KB"

def get_uptime():
    try:
        s = float(open("/proc/uptime").read().split()[0])
        return f"{int(s//3600)}h{int((s%3600)//60):02d}m"
    except: return ""

# ── Screen-Renderer ──────────────────────────────────────────
def screen_status(draw, d):
    draw_header(draw, "UCK-G2  STATUS", 0)
    ru, rt, rp = d["ram"]
    draw.text(( 2, 14), "IP",   fill=GRAY);  draw.text((22, 14), d["ip"],          fill=WHITE)
    draw.text((125, 14), time.strftime("%H:%M"),                                    fill=GRAY)
    draw.text(( 2, 24), "RAM",  fill=GRAY);  draw.text((22, 24), f"{ru}/{rt}MB",   fill=heat_color(rp))
    draw.text((108, 24), f"{rp}%",                                                  fill=heat_color(rp))
    draw.text(( 2, 34), "CPU",  fill=GRAY);  draw.text((22, 34), f"{d['cpu']}%",   fill=heat_color(d["cpu"]))
    draw.text((60, 34),  "TEMP",fill=GRAY);  draw.text((86, 34), f"{d['temp']:.0f}°C", fill=heat_color(d["temp"]/90*100))
    draw.text(( 2, 44), "UP",   fill=GRAY);  draw.text((22, 44), d["uptime"],      fill=WHITE)
    dr, dt = d["docker"]
    if dr >= 0:
        col = GREEN if dr == dt and dr > 0 else (YELLOW if dr > 0 else RED)
        draw.text((80, 44), f"Docker {dr}/{dt}", fill=col)
    draw_bar(draw, 2, 55, FB_W-4, 3, rp, heat_color(rp))

def screen_resources(draw, d):
    draw_header(draw, "CPU  MEM  DISK", 1)
    cpu = d["cpu"]; ru, rt, rp = d["ram"]; du, dt_, dp = d["disk"]
    BX, BW, PX = 38, 88, 130
    for y, label, pct in [(15,"CPU",cpu),(27,"RAM",rp),(39,"SRV",dp)]:
        draw.text((2, y), label, fill=GRAY)
        draw_bar(draw, BX, y+2, BW, 7, pct, heat_color(pct))
        draw.text((PX, y), f"{pct:3d}%", fill=heat_color(pct))
    draw.text(( 2, 52), f"{ru}/{rt}MB",  fill=GRAY)
    draw.text((82, 52), f"{du}/{dt_}GB", fill=GRAY)
    draw.text((138,52), f"{d['temp']:.0f}°", fill=heat_color(d["temp"]/90*100))

def screen_network(draw, d):
    draw_header(draw, "NETZWERK  eth0", 2)
    rx_r, tx_r = d["net_rx_rate"], d["net_tx_rate"]
    scale = max(rx_r, tx_r, 131_072)
    BX, BW = 38, 80
    draw.text((2, 15), "RX v", fill=CYAN)
    draw_bar(draw, BX, 17, BW, 7, int(rx_r/scale*100), CYAN)
    draw.text((122, 15), fmt_rate(rx_r), fill=CYAN)
    draw.text((2, 27), "TX ^", fill=ORANGE)
    draw_bar(draw, BX, 29, BW, 7, int(tx_r/scale*100), ORANGE)
    draw.text((122, 27), fmt_rate(tx_r), fill=ORANGE)
    draw.line([(2,39),(FB_W-2,39)], fill=(35,35,55))
    draw.text(( 2, 42), "Total RX:", fill=GRAY); draw.text((62, 42), fmt_total(d["net_rx_total"]), fill=WHITE)
    draw.text(( 2, 52), "Total TX:", fill=GRAY); draw.text((62, 52), fmt_total(d["net_tx_total"]), fill=WHITE)

SCREENS = [screen_status, screen_resources, screen_network]

# ── Framebuffer ──────────────────────────────────────────────
def write_fb(fb, img):
    if ROTATE:
        img = img.rotate(ROTATE)
    fb.seek(0); fb.write(to_rgb565(img)); fb.flush()

def slide(fb, old_img, new_img, steps=10):
    for i in range(1, steps+1):
        x = int(FB_W * i / steps)
        frame = Image.new("RGB", (FB_W, FB_H), BLACK)
        frame.paste(old_img.crop((x, 0, FB_W, FB_H)), (0, 0))
        frame.paste(new_img.crop((0, 0, x, FB_H)),    (FB_W-x, 0))
        write_fb(fb, frame)
        time.sleep(0.03)

def set_display_brightness(v=15):
    try: open("/sys/class/backlight/fb_sp8110/brightness","w").write(str(v))
    except: pass

# ── Hauptloop ────────────────────────────────────────────────
def main():
    print("UCK-G2 Display+LED Daemon v3 gestartet")
    set_display_brightness(15)
    led_init()
    led_logo_heartbeat()

    try:
        fb = open(FB_DEV, "wb")
    except Exception as e:
        print(f"Fehler: {e}"); sys.exit(1)

    screen_idx  = 0
    last_switch = time.time()
    last_img    = None
    rx_prev, tx_prev = get_net_bytes()
    t_prev = time.time()

    print(f"Screen 1/{NUM_SCREENS} | LEDs aktiv")

    while True:
        try:
            now = time.time()

            # Netzwerk-Delta
            rx_cur, tx_cur = get_net_bytes()
            dt = now - t_prev
            rx_rate = max(int((rx_cur - rx_prev) / dt), 0) if dt > 0 else 0
            tx_rate = max(int((tx_cur - tx_prev) / dt), 0) if dt > 0 else 0
            rx_prev, tx_prev = rx_cur, tx_cur
            t_prev = now

            # Alle Daten
            data = {
                "ip":           get_ip(),
                "ram":          get_ram(),
                "cpu":          get_cpu_pct(),
                "temp":         get_temp(),
                "docker":       get_docker(),
                "disk":         get_disk(),
                "uptime":       get_uptime(),
                "net_rx_rate":  rx_rate,
                "net_tx_rate":  tx_rate,
                "net_rx_total": rx_cur,
                "net_tx_total": tx_cur,
            }

            # ── LEDs aktualisieren ────────────────────────────
            ru, rt, rp = data["ram"]
            dr, dt_    = data["docker"]
            led_set_status(rp, data["cpu"], dr, dt_)
            led_set_network(rx_rate, tx_rate)

            # ── Screen-Wechsel ────────────────────────────────
            if now - last_switch >= SCREEN_SECS:
                new_idx  = (screen_idx + 1) % NUM_SCREENS
                new_img  = Image.new("RGB", (FB_W, FB_H), BLACK)
                SCREENS[new_idx](ImageDraw.Draw(new_img), data)
                if last_img:
                    slide(fb, last_img, new_img)
                else:
                    write_fb(fb, new_img)
                screen_idx  = new_idx
                last_switch = now
                last_img    = new_img.copy()
                print(f"-> Screen {screen_idx+1}/{NUM_SCREENS}")
                time.sleep(UPDATE_SECS)
                continue

            # ── Frame zeichnen ────────────────────────────────
            img  = Image.new("RGB", (FB_W, FB_H), BLACK)
            draw = ImageDraw.Draw(img)
            SCREENS[screen_idx](draw, data)

            # Timer-Balken (wie lange bis zum nächsten Wechsel)
            elapsed = now - last_switch
            draw.line([(0, FB_H-1), (int(FB_W * elapsed / SCREEN_SECS), FB_H-1)],
                      fill=(30, 30, 70))

            write_fb(fb, img)
            last_img = img.copy()

        except KeyboardInterrupt:
            print("\nBeendet – LEDs aus.")
            led_logo_off()
            led_write(LED_BLUE,  0)
            led_write(LED_WHITE, 0)
            break
        except Exception as e:
            print(f"Fehler: {e}", flush=True)

        time.sleep(UPDATE_SECS)

    fb.close()
    try:
        with open(FB_DEV, "wb") as f: f.write(bytes(FB_W * FB_H * 2))
    except: pass

if __name__ == "__main__":
    main()