# Own my Unifi Cloud KEy Gen2

UCK-G2 Repurpose Suite: Debloat, Docker & Custom DisplayThis repository contains a suite of scripts designed to transform a Ubiquiti Cloud Key Gen2 (Plus) into a lean, high-performance Docker host. By disabling resource-heavy UniFi services and replacing the factory OLED UI, you can reclaim system resources for your own homelab services.

[!WARNING]Experimental: These scripts will stop and disable original UniFi services like Network and Protect. This is intended for users repurposing the hardware for Docker, Pi-hole, and other custom applications.

📦 Component Overview1. uck-debloat.shThe core script that strips down the OS and prepares the Docker environment:Service Cleanup: Stops and disables over 15 UniFi-specific services (e.g., MongoDB, PostgreSQL, unifi-core) to significantly reduce RAM usage.Storage Optimization: Creates a dedicated Docker data-root on /srv (utilizing the ~19GB HDD/SSD space on the Plus model) to prevent wearing out the internal eMMC flash.

Docker Engine: Automatically installs the latest Docker CE (ARM64) and Docker Compose plugin.System Tuning: Optimizes Kernel parameters such as swappiness and enables ip_forwarding for stable container networking.Default Stack: Deploys a starter docker-compose.yml including Pi-hole (DNS) and Avahi (mDNS reflector).2. uck-display-install.sh

The visual upgrade for the integrated OLED screen:Dependency Management: Handles the installation of the Python Pillow library required for rendering.UI Replacement: Disables the factory ck-ui and installs the custom uck-display.py as a system service.Systemd Integration: Configures a robust background service with automatic restarts and logging.

🚀 Installation & Usage
Step 1: System Debloat & Docker SetupRun the debloat script to clean the system and install Docker.Bash# Download and execute the debloat script

curl -O https://raw.githubusercontent.com/mav3r10k/OWN_UCKGEN2/main/uck-debloat.sh
sudo bash uck-debloat.sh | tee /tmp/debloat.log

Step 2: Install Custom Display DaemonAfter the system is prepared, install the new OLED interface.Bash# Download and execute the display installer

curl -O https://raw.githubusercontent.com/mav3r10k/OWN_UCKGEN2/main/uck-display-install.sh
sudo bash uck-display-install.sh

Step 3: Manage ContainersYour Docker environment is now ready at /srv/compose.
Bash
cd /srv/compose
docker compose up -d

📊 System Impact (Typical Results)MetricFactory StateAfter DebloatRAM Usage~1.6 GB~400 MBStorage RootInternal eMMCHDD/SSD (/srv)OLED UIUbiquiti DefaultCustom Stats (v3)🛠️ MaintenanceCheck the Display Logs:Bashjournalctl -u uck-display -f
Monitor System Services:Bashsystemctl status uck-display.service
Restart the Display Daemon:Bashsystemctl restart uck-display


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
