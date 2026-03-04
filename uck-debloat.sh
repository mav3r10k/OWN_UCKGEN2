#!/bin/bash
# ============================================================
#  UCK-G2 Debloat & Docker-Setup Script
#  Getestet auf: UniFi Cloud Key Gen2 (OverlayFS, ARM64)
#  Aufruf: bash uck-debloat.sh | tee /tmp/debloat.log
# ============================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'

info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()      { echo -e "${GREEN}[ OK ]${NC}  $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
error()   { echo -e "${RED}[FAIL]${NC}  $1"; }
heading() { echo -e "\n${BOLD}══════════════════════════════════════${NC}"; \
            echo -e "${BOLD}  $1${NC}"; \
            echo -e "${BOLD}══════════════════════════════════════${NC}"; }

# Root-Check
if [ "$(id -u)" -ne 0 ]; then
  error "Bitte als root ausführen: sudo bash $0"
  exit 1
fi

heading "UCK-G2 Debloat Script — $(date '+%Y-%m-%d %H:%M')"

# ── Status vor dem Cleanup ────────────────────────────────────
heading "1/6 — Ausgangszustand"
echo "--- RAM ---"
free -m | awk 'NR==2{printf "  Gesamt: %dMB | Belegt: %dMB | Frei: %dMB\n",$2,$3,$4}'
echo "--- Speicher ---"
df -h / /srv 2>/dev/null | awk 'NR>1{printf "  %-30s %s von %s\n",$6,$3,$2}'

# ── UniFi-Dienste stoppen ─────────────────────────────────────
heading "2/6 — Stoppe & deaktiviere UniFi-Dienste"

STOP_SERVICES=(
  "unifi"
  "unifi-mongodb"
  "postgresql@14-main"
  "unifi-core"
  "unifi-directory"
  "unifi-identity-update"
  "ucs-agent"
  "uos-agent"
  "uos-discovery-client"
  "uid-agent"
  "ulp-go"
  "ubnt-systemhub"
  "infctld"
  "gw-ip-monitor"
  "analytic-report-monitor"
)

# Diese Dienste BEHALTEN (Display, SSH, Netzwerk, Cron)
KEEP_SERVICES=("ck-ui" "nginx" "avahi-daemon" "ssh" "cron" "systemd-networkd")

for svc in "${STOP_SERVICES[@]}"; do
  if systemctl is-active --quiet "$svc" 2>/dev/null; then
    systemctl stop "$svc"    2>/dev/null && \
    systemctl disable "$svc" 2>/dev/null && \
    ok "Gestoppt & deaktiviert: $svc" || warn "Fehler bei: $svc"
  else
    info "Nicht aktiv (übersprungen): $svc"
  fi
done

# ── /srv für Docker vorbereiten ───────────────────────────────
heading "3/6 — Richte /srv als Docker-Datenpfad ein"

# /srv hat 19GB freien Speicher — ideal für Docker
mkdir -p /srv/docker
mkdir -p /srv/containers/pihole/etc-pihole
mkdir -p /srv/containers/pihole/etc-dnsmasq.d
mkdir -p /srv/containers/avahi
mkdir -p /srv/compose

ok "Verzeichnisstruktur unter /srv erstellt"
df -h /srv | awk 'NR==2{printf "  Verfügbar auf /srv: %s von %s\n",$4,$2}'

# ── Docker installieren ───────────────────────────────────────
heading "4/6 — Docker (ARM64)"

if command -v docker &>/dev/null; then
  ok "Docker bereits installiert: $(docker --version | cut -d' ' -f3 | tr -d ',')"
else
  info "Installiere Docker..."
  apt-get update -qq

  apt-get install -y -qq \
    ca-certificates curl gnupg lsb-release

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=arm64 signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -qq
  apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io docker-compose-plugin

  ok "Docker installiert: $(docker --version | cut -d' ' -f3 | tr -d ',')"
fi

# Docker-Konfiguration: Daten nach /srv
info "Konfiguriere Docker data-root → /srv/docker"
cat > /etc/docker/daemon.json << 'EOF'
{
  "data-root": "/srv/docker",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

systemctl enable docker 2>/dev/null
systemctl restart docker
ok "Docker läuft, data-root: /srv/docker"

# ── Kernel-Parameter & System-Tuning ─────────────────────────
heading "5/6 — System-Optimierungen"

# IP-Forwarding (für Docker-Netzwerke nötig)
grep -q "net.ipv4.ip_forward" /etc/sysctl.conf || \
cat >> /etc/sysctl.conf << 'EOF'

# UCK-G2 Docker Optimierungen
net.ipv4.ip_forward=1
net.bridge.bridge-nf-call-iptables=1
vm.swappiness=10
net.core.rmem_max=4194304
net.core.wmem_max=4194304
EOF

sysctl -p > /dev/null 2>&1
ok "Kernel-Parameter gesetzt (ip_forward, swappiness=10)"

# Display-Helligkeit auf Maximum
info "Display-Helligkeit auf Maximum..."
MAX_BL=$(cat /sys/class/backlight/fb_sp8110/max_brightness 2>/dev/null || echo "15")
echo "$MAX_BL" | tee /sys/class/backlight/fb_sp8110/brightness > /dev/null 2>&1 && \
  ok "Display-Helligkeit: $MAX_BL/$MAX_BL" || \
  warn "Helligkeit konnte nicht gesetzt werden"

# ── Docker Compose für Standard-Services ─────────────────────
info "Erstelle /srv/compose/docker-compose.yml..."
cat > /srv/compose/docker-compose.yml << 'EOF'
# UCK-G2 Docker Compose
# Starten: cd /srv/compose && docker compose up -d
# Stoppen: cd /srv/compose && docker compose down

services:

  # ── Pi-hole (DNS + Ad-Blocking) ──────────────────────────────
  pihole:
    image: pihole/pihole:latest
    container_name: pihole
    network_mode: host
    restart: unless-stopped
    environment:
      TZ: "Europe/Berlin"
      WEBPASSWORD: "changeme"          # ← Bitte ändern!
      DNSMASQ_LISTENING: "all"
    volumes:
      - /srv/containers/pihole/etc-pihole:/etc/pihole
      - /srv/containers/pihole/etc-dnsmasq.d:/etc/dnsmasq.d
    cap_add:
      - NET_ADMIN
      - NET_RAW

  # ── Avahi mDNS Reflector ─────────────────────────────────────
  avahi:
    image: flungo/avahi:latest
    container_name: avahi
    network_mode: host
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    volumes:
      - /srv/containers/avahi:/etc/avahi/avahi-daemon.conf.d

EOF

ok "docker-compose.yml erstellt unter /srv/compose/"

# ── Abschlussbericht ──────────────────────────────────────────
heading "6/6 — Fertig! Abschlussbericht"

echo ""
echo -e "${GREEN}--- RAM nach Cleanup ---${NC}"
free -m | awk 'NR==2{printf "  Gesamt: %dMB | Belegt: %dMB | Frei: %dMB\n",$2,$3,$4}'

echo ""
echo -e "${GREEN}--- Speicher ---${NC}"
df -h / /srv | awk 'NR>1{printf "  %-30s %s verfügbar\n",$6,$4}'

echo ""
echo -e "${GREEN}--- Docker ---${NC}"
docker info --format "  Version: {{.ServerVersion}} | Root: {{.DockerRootDir}}" 2>/dev/null

echo ""
echo -e "${GREEN}--- Noch laufende Dienste ---${NC}"
systemctl list-units --type=service --state=running --no-legend \
  | awk '{print "  "$1}'

echo ""
echo -e "${BOLD}${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  UCK-G2 Debloat abgeschlossen!         ║${NC}"
echo -e "${BOLD}${GREEN}║                                        ║${NC}"
echo -e "${BOLD}${GREEN}║  Nächste Schritte:                     ║${NC}"
echo -e "${BOLD}${GREEN}║  1. Display-Daemon installieren        ║${NC}"
echo -e "${BOLD}${GREEN}║     → bash /srv/uck-display-install.sh ║${NC}"
echo -e "${BOLD}${GREEN}║  2. Container starten                  ║${NC}"
echo -e "${BOLD}${GREEN}║     → cd /srv/compose                  ║${NC}"
echo -e "${BOLD}${GREEN}║     → docker compose up -d             ║${NC}"
echo -e "${BOLD}${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
