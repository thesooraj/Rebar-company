"""
wifi_check.py — The Rebar Company
Checks if the device is connected to the office WiFi network.
"""

import subprocess
import platform
import database as db


def get_current_ssid() -> str:
    """Get the name of the currently connected WiFi network."""
    try:
        system = platform.system()

        if system == "Darwin":  # Mac
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework"
                 "/Versions/Current/Resources/airport", "-I"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if " SSID:" in line:
                    return line.strip().split(": ", 1)[1].strip()

        elif system == "Linux":
            result = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True, text=True
            )
            return result.stdout.strip()

        elif system == "Windows":
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "SSID" in line and "BSSID" not in line:
                    return line.strip().split(": ", 1)[1].strip()

    except Exception:
        pass

    return ""


def is_on_office_wifi() -> bool:
    """
    Returns True if WiFi lock is disabled OR
    if the current SSID matches the office SSID.
    """
    wifi_lock_enabled = db.get_setting("wifi_lock_enabled", "0")
    if wifi_lock_enabled != "1":
        return True  # WiFi lock is off — always allow

    office_ssid   = db.get_setting("office_ssid", "")
    current_ssid  = get_current_ssid()

    if not office_ssid:
        return True  # No office SSID configured — allow

    return current_ssid.lower() == office_ssid.lower()


def get_wifi_status() -> dict:
    """Return a dict with WiFi status info for display."""
    wifi_lock_enabled = db.get_setting("wifi_lock_enabled", "0")
    office_ssid       = db.get_setting("office_ssid", "")
    current_ssid      = get_current_ssid()
    on_office         = is_on_office_wifi()

    return {
        "enabled":       wifi_lock_enabled == "1",
        "office_ssid":   office_ssid,
        "current_ssid":  current_ssid,
        "on_office_wifi": on_office,
    }