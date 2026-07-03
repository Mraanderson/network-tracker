# Network Monitor & Dashboard Tracker

AI overview below that will be cleaned up to make sense to a human, soon.

A lightweight, automated network discovery and asset tracking tool designed for home labs.

The script performs a periodic subnet sweep using nmap, stores device states (online/offline/vendor) in an SQLite database, and generates both a modern, dark-mode HTML dashboard and a lightweight text payload for external hardware displays (like a Raspberry Pi Zero).

# Features
- Dynamic Asset Discovery: Automatically detects new devices on the local subnet without manual configuration.
- Vendor Identification: Maps MAC addresses to hardware manufacturers using Nmap's database.
- Persistent State Tracking: Tracks historical presence and prunes stale devices unseen for more than 7 days.
- Dual Output Modes:
- HTML Dashboard: A beautifully styled, mobile-responsive dark-mode status page.
- Text Payload (status.txt): A raw string optimized for ultra-low-overhead parsing by microcontrollers or single-board computers.

# System Architecture
The workflow follows a simple automated pipeline:

Cron Job] -> [tracker.py] -> [nmap Subnet Scan] -> [SQLite DB Update]
|

[index.html (Web)]            [status.txt (Pi)]

# Prerequisites

1. Dependencies
The script relies on nmap for network discovery and requires root/sudo privileges to perform layer-2 MAC address resolution on local networks.
Command to install dependencies:
sudo apt update && sudo apt install nmap apache2 python3

2. Directory Setup
Ensure the local application folder and the Apache web server directory exist and have the correct permissions.

Commands to configure folders:

  mkdir -p ~/network-monitor
  sudo mkdir -p /var/www/html/netmap-dashboard
  sudo chown -R $USER:$USER /var/www/html/netmap-dashboard

Installation & Setup
Move tracker.py into your ~/network-monitor/ directory.

Run the script manually once to verify database initialization and dashboard generation using the command:
  python3 ~/network-monitor/tracker.py

Open your browser and navigate to http://localhost/netmap-dashboard/ to view the generated web UI.

# Automation (Crontab)

To keep the dashboard updated automatically every 5 minutes, add the script to your system's crontab. Because nmap requires root privileges to fetch MAC/Vendor data, use the root crontab or ensure your user has passwordless sudo access for nmap.

Open the root crontab configuration with the command:

  sudo crontab -e

Add the following exact cron string line at the bottom of the file:

  */5 * * * * cd /home/user/network-monitor && /usr/bin/python3 tracker.py > /home/user/network-monitor/cron.log 2>&1

Note: Be sure to update /home/user/ with your actual absolute home directory path.

File Structure
Visual layout of the directory map:

~/network-monitor/
├── network.db       (SQLite database storing host histories)
├── tracker.py       (Main Python scanning and generation script)
└── cron.log         (Standard output & error logs from cron runs)
/var/www/html/netmap-dashboard/
├── index.html       (Auto-generated dark-mode web dashboard)
└── status.txt       

# License
This project is open-source and free to use for personal home-lab environments.
