Hier ist dein Text sauber und strukturiert im **Markdown-Format** formatiert:

---

# Own my UniFi Cloud Key Gen2

## UCK-G2 Repurpose Suite: Debloat, Docker & Custom Display

This repository contains a suite of scripts designed to transform a **Ubiquiti Cloud Key Gen2 (Plus)** into a lean, high-performance Docker host. By disabling resource-heavy UniFi services and replacing the factory OLED UI, you can reclaim system resources for your own homelab services.

> ⚠️ **WARNING – Experimental**
> These scripts will stop and disable original UniFi services like Network and Protect.
> This is intended for users repurposing the hardware for Docker, Pi-hole, and other custom applications.

---

## 📦 Component Overview

### 1️⃣ `uck-debloat.sh`

The core script that strips down the OS and prepares the Docker environment:

* **Service Cleanup**
  Stops and disables over 15 UniFi-specific services (e.g., MongoDB, PostgreSQL, unifi-core) to significantly reduce RAM usage.

* **Storage Optimization**
  Creates a dedicated Docker `data-root` on `/srv` (utilizing the ~19GB HDD/SSD space on the Plus model) to prevent wearing out the internal eMMC flash.

* **Docker Engine**
  Automatically installs the latest Docker CE (ARM64) and Docker Compose plugin.

* **System Tuning**
  Optimizes kernel parameters such as `swappiness` and enables `ip_forwarding` for stable container networking.

* **Default Stack**
  Deploys a starter `docker-compose.yml` including:

  * Pi-hole (DNS)
  * Avahi (mDNS reflector)

---

### 2️⃣ `uck-display-install.sh`

The visual upgrade for the integrated OLED screen:

* **Dependency Management**
  Installs the Python Pillow library required for rendering.

* **UI Replacement**
  Disables the factory `ck-ui` and installs the custom `uck-display.py` as a system service.

* **Systemd Integration**
  Configures a robust background service with automatic restarts and logging.

---

# 🚀 Installation & Usage

## Step 1: System Debloat & Docker Setup

Download and execute the debloat script:

```bash
curl -O https://raw.githubusercontent.com/mav3r10k/OWN_UCKGEN2/main/uck-debloat.sh
sudo bash uck-debloat.sh | tee /tmp/debloat.log
```

---

## Step 2: Install Custom Display Daemon

```bash
curl -O https://raw.githubusercontent.com/mav3r10k/OWN_UCKGEN2/main/uck-display-install.sh
sudo bash uck-display-install.sh
```

---

## Step 3: Manage Containers

Your Docker environment is now ready at `/srv/compose`.

```bash
cd /srv/compose
docker compose up -d
```

---

# 📊 System Impact (Typical Results)

| Metric       | Factory State    | After Debloat     |
| ------------ | ---------------- | ----------------- |
| RAM Usage    | ~1.6 GB          | ~400 MB           |
| Storage Root | Internal eMMC    | HDD/SSD (`/srv`)  |
| OLED UI      | Ubiquiti Default | Custom Stats (v3) |

---

# 🛠️ Maintenance

## Check Display Logs

```bash
journalctl -u uck-display -f
```

## Monitor System Services

```bash
systemctl status uck-display.service
```

## Restart Display Daemon

```bash
systemctl restart uck-display
```

---

# 🤝 Contributions

Feel free to submit Pull Requests to:

* Add new screens to the Python daemon
* Optimize the debloat list for newer firmware versions

---

# UCK-G2 Custom Display & LED Daemon v3

This script is a specialized system monitoring tool designed for the **Ubiquiti Cloud Key Gen2 (Plus)**. It utilizes:

* The integrated OLED display (`/dev/fb0`)
* The chassis LEDs

It provides real-time feedback on system health, resource usage, and network activity.

---

# 🚀 Features

## 🖥️ Display (160x60px OLED)

The display rotates through three information screens every **2 minutes** with a smooth slide transition:

### 1️⃣ System Status

* IP address
* Uptime
* CPU / RAM usage
* Temperature
* Docker container status

### 2️⃣ Resource Monitor

Detailed bar charts for:

* CPU load
* Memory usage
* Disk occupancy (focused on `/srv`)

### 3️⃣ Network Monitor

* Live traffic (RX/TX) for the `eth0` interface
* Total data statistics

---

## 💡 LED Control

* **U-Logo (White)**
  Pulsates in "Heartbeat" mode during normal operation
  Flashes rapidly during critical load

* **Blue LED**

  * On = OK
  * Blinking = High Load
  * Off = Docker issues / All containers stopped

* **White LED**
  Dynamic brightness based on real-time network throughput

---

# 🛠️ Installation

## 1️⃣ Install Dependencies

```bash
apt-get update
apt-get install -y python3-pil
```

---

## 2️⃣ Deploy the Script

Copy the script to `/usr/local/bin/uck-daemon.py` and make it executable:

```bash
chmod +x /usr/local/bin/uck-daemon.py
```

---

## 3️⃣ Setup Autostart (Systemd)

Create the service file at:

```
/etc/systemd/system/uck-daemon.service
```

```ini
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
```

---

## 4️⃣ Enable and Start the Service

```bash
systemctl daemon-reload
systemctl enable uck-daemon.service
systemctl start uck-daemon.service
```

---

# ⚠️ Troubleshooting

## Encoding Errors (Latin-1)

If you see the error:

```
codec can't encode character '\u2193'
```

Check:

```bash
journalctl -u uck-daemon
```

Ensure the following line exists in your service file:

```
Environment=PYTHONIOENCODING=utf-8
```

Alternatively, replace arrow symbols:

* `↑` → `^`
* `↓` → `v`

---

## Framebuffer Access

The script requires direct write access to:

* `/dev/fb0`
* `/sys/class/leds/`

It must be run with **root privileges**.

---

# ⚙️ Configuration

You can customize behavior by editing the constants at the top of the script:

* `UPDATE_SECS` → Frequency of data updates (Default: 5s)
* `SCREEN_SECS` → Screen switch interval (Default: 120s)
* `THRESH_WARN / THRESH_CRIT` → Thresholds for:

  * Color changes (Green → Yellow → Red)
  * LED alerts

---
