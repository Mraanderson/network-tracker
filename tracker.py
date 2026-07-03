
# -*- coding: utf-8 -*-
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Configurations
SUBNET = "192.168.1.0/24"
DB_FILE = os.path.expanduser("~/network-monitor/network.db")
WEB_DIR = "/var/www/html/netmap-dashboard"
HTML_FILE = os.path.join(WEB_DIR, "index.html")
TXT_FILE = os.path.join(WEB_DIR, "status.txt")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            mac TEXT PRIMARY KEY,
            ip TEXT,
            vendor TEXT,
            first_seen TEXT,
            last_seen TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

def scan_network():
    xml_output = "/tmp/scan.xml"
    os.system(f"sudo nmap -sn {SUBNET} -oX {xml_output} > /dev/null")

    if not os.path.exists(xml_output):
        return {}

    current_hosts = {}
    tree = ET.parse(xml_output)
    root = tree.getroot()

    for host in root.findall('host'):
        ip = "Unknown"
        mac = None
        vendor = "Unknown"

        for addr in host.findall('address'):
            addr_type = addr.get('addrtype')
            if addr_type == 'ipv4':
                ip = addr.get('addr')
            elif addr_type == 'mac':
                mac = addr.get('addr').upper()
                if addr.get('vendor'):
                    vendor = addr.get('vendor')

        if mac:
            current_hosts[mac] = {'ip': ip, 'vendor': vendor}

    os.system(f"sudo rm -f {xml_output}")
    return current_hosts

def update_database(current_hosts):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("UPDATE devices SET status='offline'")

    for mac, info in current_hosts.items():
        cursor.execute("SELECT first_seen FROM devices WHERE mac=?", (mac,))
        row = cursor.fetchone()

        if row is None:
            cursor.execute('''
                INSERT INTO devices (mac, ip, vendor, first_seen, last_seen, status)
                VALUES (?, ?, ?, ?, ?, 'online')
            ''', (mac, info['ip'], info['vendor'], now_str, now_str))
        else:
            cursor.execute('''
                UPDATE devices
                SET ip=?, vendor=?, last_seen=?, status='online'
                WHERE mac=?
            ''', (info['ip'], info['vendor'], now_str, mac))

    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM devices WHERE last_seen < ?", (seven_days_ago,))

    conn.commit()
    conn.close()

def generate_dashboard():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Fetch stats
    cursor.execute("SELECT COUNT(*) FROM devices WHERE status='online'")
    online_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM devices WHERE status='offline'")
    offline_count = cursor.fetchone()[0]

    # Fetch all records sorted by status and IP
    cursor.execute("SELECT ip, mac, vendor, last_seen, status FROM devices ORDER BY status DESC, ip ASC")
    devices = cursor.fetchall()
    conn.close()

    # 1. Generate lightweight status.txt for the Pi Zero later
    with open(TXT_FILE, "w") as f:
        f.write(f"ONLINE:{online_count}|OFFLINE:{offline_count}|TOTAL:{online_count + offline_count}")

    # 2. Generate the HTML Dashboard
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Network Map</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #121212; color: #e0e0e0; margin: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .stats {{ display: flex; gap: 15px; }}
        .stat-card {{ background: #1e1e1e; padding: 10px 20px; border-radius: 6px; border: 1px solid #333; }}
        .stat-card.online {{ border-left: 4px solid #4caf50; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e1e1e; border-radius: 6px; overflow: hidden; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #2a2a2a; color: #aaa; }}
        .badge {{ padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
        .badge.online {{ background: #2e7d32; color: #fff; }}
        .badge.offline {{ background: #c62828; color: #fff; }}
        tr:hover {{ background: #252525; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Home Network Map</h2>
            <div class="stats">
                <div class="stat-card online">Online: <strong>{online_count}</strong></div>
                <div class="stat-card">Tracked Offline: <strong>{offline_count}</strong></div>
            </div>
        </div>
        <p style="color: #888; font-size: 13px;">Last updated: {now_str} (Refreshes every 5 min)</p>
        <table>
            <thead>
                <tr>
                    <th>Status</th>
                    <th>IP Address</th>
                    <th>MAC Address</th>
                    <th>Vendor</th>
                    <th>Last Seen</th>
                </tr>
            </thead>
            <tbody>
    """

    for dev in devices:
        ip, mac, vendor, last_seen, status = dev
        badge_class = "online" if status == "online" else "offline"
        html_content += f"""
                <tr>
                    <td><span class="badge {badge_class}">{status.upper()}</span></td>
                    <td><strong>{ip}</strong></td>
                    <td style="font-family: monospace; color: #aaa;">{mac}</td>
                    <td>{vendor}</td>
                    <td style="color: #888; font-size: 13px;">{last_seen}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
    """

    with open(HTML_FILE, "w") as f:
        f.write(html_content)

if __name__ == "__main__":
    init_db()
    print("Scanning network...")
    discovered = scan_network()
    print(f"Found {len(discovered)} active devices. Updating database...")
    update_database(discovered)
    print("Generating Dashboard outputs...")
    generate_dashboard()
    print("Done! Check Apache web folder.")
