# Own my Unifi Cloud KEy Gen2

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
