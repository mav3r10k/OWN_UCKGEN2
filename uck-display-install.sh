#!/bin/bash
# ============================================================
#  UCK-G2 Display Daemon Installer
#  Installiert uck-display.py und ersetzt ck-ui
#  Aufruf: bash uck-display-install.sh
# ============================================================

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
NC='\033[0m'; BOLD='\033[1m'

ok()   { echo -e "${GREEN}[ OK ]${NC}  $1"; }
info() { echo -e "${BLUE}[INFO]${NC}  $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }

if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte als root ausführen!"; exit 1
fi

echo -e "\n${BOLD}══ UCK-G2 Display Daemon Installer ══${NC}\n"

# ── 1. Pillow installieren ────────────────────────────────────
info "Installiere Python-Abhängigkeit: pillow..."
pip3 install pillow --break-system-packages -q && \
  ok "pillow installiert" || \
  warn "pip3 nicht gefunden — versuche apt..."
  apt-get install -y -qq python3-pil 2>/dev/null && ok "python3-pil via apt installiert"

# ── 2. Daemon kopieren ────────────────────────────────────────
info "Kopiere Display-Daemon nach /usr/local/bin/..."
cp uck-display.py /usr/local/bin/uck-display.py
chmod +x /usr/local/bin/uck-display.py
ok "uck-display.py installiert"

# ── 3. Schnelltest ───────────────────────────────────────────
info "Kurztest: Framebuffer erreichbar?"
if [ -w /dev/fb0 ]; then
  ok "/dev/fb0 beschreibbar"
else
  warn "/dev/fb0 nicht beschreibbar — prüfe Berechtigungen"
fi

# ── 4. ck-ui stoppen ─────────────────────────────────────────
info "Stoppe & deaktiviere ck-ui..."
systemctl stop ck-ui    2>/dev/null && ok "ck-ui gestoppt"    || warn "ck-ui war nicht aktiv"
systemctl disable ck-ui 2>/dev/null && ok "ck-ui deaktiviert" || true

# ── 5. systemd-Unit erstellen ─────────────────────────────────
info "Erstelle systemd-Dienst: uck-display..."
cat > /etc/systemd/system/uck-display.service << 'EOF'
[Unit]
Description=UCK-G2 Custom Display Daemon
After=network.target docker.service
Wants=docker.service

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/uck-display.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable uck-display
systemctl start  uck-display
sleep 2

if systemctl is-active --quiet uck-display; then
  ok "uck-display.service läuft!"
else
  warn "Dienst nicht aktiv — Log prüfen:"
  echo ""
  journalctl -u uck-display -n 20 --no-pager
fi

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Display-Daemon installiert!         ║${NC}"
echo -e "${BOLD}${GREEN}║                                      ║${NC}"
echo -e "${BOLD}${GREEN}║  Status:  systemctl status uck-display║${NC}"
echo -e "${BOLD}${GREEN}║  Log:     journalctl -fu uck-display  ║${NC}"
echo -e "${BOLD}${GREEN}║  Neustart: systemctl restart uck-display║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
