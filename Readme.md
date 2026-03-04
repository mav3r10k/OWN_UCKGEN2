# Own my Unifi Cloud KEy Gen2

UCK-G2 Repurpose Suite: Debloat, Docker & Custom DisplayThis repository contains a suite of scripts to transform a Ubiquiti Cloud Key Gen2 (Plus) into a lean, powerful Docker host. It disables resource-heavy UniFi services and replaces the default OLED UI with a custom, real-time system monitor.[!WARNING]Experimental: Running these scripts will stop and disable original UniFi services (Network, Protect, etc.). This is intended for users who want to repurpose the hardware for Docker, Pi-hole, and other homelab services.📦 Included Scripts1. uck-debloat.shThe "heavy lifter" script that prepares the hardware for a new life.Service Cleanup: Stops and disables 15+ UniFi services (MongoDB, PostgreSQL, Identity, etc.) to free up RAM.Storage Optimization: Maps Docker's data-root to /srv (which has ~19GB on the Gen2 Plus) to protect the internal flash.Docker Engine: Installs the latest Docker CE (ARM64) and Docker Compose.Kernel Tuning: Optimizes swappiness and enables ip_forwarding for container networking.Default Stack: Deploys a starter docker-compose.yml featuring Pi-hole and Avahi.2. uck-display-install.shThe visual upgrade for your device.Dependency Management: Automatically installs Python Pillow for OLED rendering.UI Replacement: Disables the factory ck-ui service and replaces it with your custom uck-display.py.Systemd Integration: Sets up a robust background service with auto-restart and logging.🚀 Quick StartStep 1: Debloat and Install DockerExecute the debloat script to clean the system and install the Docker environment.Bashcurl -O https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/uck-debloat.sh
sudo bash uck-debloat.sh | tee /tmp/debloat.log
Step 2: Install the Custom DisplayOnce the system is clean, install the custom display daemon to regain control over the OLED screen.Bashcurl -O https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/uck-display-install.sh
sudo bash uck-display-install.sh
Step 3: Launch your ContainersNavigate to the pre-configured compose directory and start your services:Bashcd /srv/compose
docker compose up -d
📊 System Overview (Post-Debloat)After running the suite, the resource footprint on the UCK-G2 is significantly reduced:MetricBeforeAfterRAM Usage~1.6 GB~400 MBActive Services20+ UniFi DaemonsDocker + System BasicsStorage RootInternal eMMCHDD/SSD (/srv)🛠️ Maintenance & LogsMonitor the Display Daemon:Bashjournalctl -fu uck-display
Check Docker Status:Bashdocker ps
Adjusting Display Brightness:The script automatically sets the brightness to maximum, but you can manually adjust it via:Bashecho 15 > /sys/class/backlight/fb_sp8110/brightness
🤝 ContributionsFeel free to submit Pull Requests to add new screens to the Python daemon or optimize the debloat list for newer firmware versions.

---

UCK-G2 Custom Display & LED Daemon v3
This script is a specialized system monitoring tool designed for the Ubiquiti Cloud Key Gen2 (Plus). It utilizes the integrated OLED display (/dev/fb0) and the chassis LEDs to provide real-time feedback on system health, resource usage, and network activity.

🚀 Features
🖥️ Display (160x60px OLED)
The display rotates through three information screens every 2 minutes with a smooth slide transition:

System Status: IP address, Uptime, CPU/RAM usage, temperature, and Docker container status.

Resource Monitor: Detailed bar charts for CPU load, Memory usage, and Disk occupancy (focused on /srv).

Network Monitor: Live traffic (RX/TX) for the eth0 interface including total data statistics.

💡 LED Control
U-Logo (White): Pulsates in "Heartbeat" mode during normal operation; flashes rapidly during critical load.

Blue LED: Indicates system health (On = OK, Blinking = High Load, Off = Docker issues/All containers stopped).

White LED: Dynamic brightness based on real-time network throughput.

🛠️ Installation
1. Install Dependencies
The script requires the Python Imaging Library (Pillow):

Bash

apt-get update
apt-get install -y python3-pil
2. Deploy the Script
Copy the script to /usr/local/bin/uck-daemon.py and ensure it is executable:

Bash

chmod +x /usr/local/bin/uck-daemon.py
3. Setup Autostart (Systemd)
Create the service file at /etc/systemd/system/uck-daemon.service:

Ini, TOML

[Unit]
Description=UCK-G2 Custom Display Daemon
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/uck-daemon.py
Restart=always
User=root
# Crucial for rendering special characters (arrows) on the display:
Environment=PYTHONIOENCODING=utf-8
Environment=LANG=en_US.UTF-8

[Install]
WantedBy=multi-user.target
4. Enable and Start the Service
Bash

systemctl daemon-reload
systemctl enable uck-daemon.service
systemctl start uck-daemon.service
⚠️ Troubleshooting
Encoding Errors (Latin-1)
If you see the error codec can't encode character '\u2193' in your logs (journalctl -u uck-daemon), ensure that the Environment=PYTHONIOENCODING=utf-8 line is present in your service file. Alternatively, replace the arrow symbols (↑, ↓) in the Python source code with standard ASCII characters (^, v).

Framebuffer Access
The script requires direct write access to /dev/fb0 and /sys/class/leds/. It must be run with root privileges.

⚙️ Configuration
You can customize the behavior by editing the constants at the top of the script:

UPDATE_SECS: Frequency of data updates (Default: 5s).

SCREEN_SECS: Time before switching to the next screen (Default: 120s).

THRESH_WARN / THRESH_CRIT: Thresholds for color changes (Green ➔ Yellow ➔ Red) and LED alerts.
