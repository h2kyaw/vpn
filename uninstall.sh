#!/bin/bash
# Remove installed hotspot system files and runtime rules.
# Project source files in this repository are left intact.

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
POLICY_SCRIPT="$PROJECT_DIR/configs/90-hotspot-vpn-policy"

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}[WARNING] This removes installed hotspot services/config from the system.${NC}"
echo -e "${YELLOW}Project source files in this repository will not be deleted.${NC}"
read -r -p "Continue? (y/N): " reply
if [[ ! "$reply" =~ ^[Yy]$ ]]; then
  exit 1
fi

sudo systemctl stop hostapd dnsmasq AdGuardHome 2>/dev/null || true
sudo systemctl disable hostapd dnsmasq AdGuardHome 2>/dev/null || true
sudo systemctl stop wpa_supplicant 2>/dev/null || true

if [ -x "$POLICY_SCRIPT" ]; then
  sudo "$POLICY_SCRIPT" tun0 cleanup
elif [ -x /etc/NetworkManager/dispatcher.d/90-hotspot-vpn-policy ]; then
  sudo /etc/NetworkManager/dispatcher.d/90-hotspot-vpn-policy tun0 cleanup
fi
sudo netfilter-persistent save

sudo rm -f /etc/hostapd/hostapd.conf
sudo rm -f /etc/systemd/system/hostapd.service.d/override.conf
sudo rm -f /etc/dnsmasq.conf
sudo rm -f /etc/NetworkManager/dispatcher.d/20-hotspot-manager
sudo rm -f /etc/NetworkManager/dispatcher.d/90-hotspot-vpn-policy
sudo rm -f /usr/local/bin/hotspot-manager.py
sudo systemctl daemon-reload

sudo ip addr flush dev wlan0 2>/dev/null || true

sed -i '/^alias hotspot=/d; /^alias hs=/d; /^alias hf=/d' "$HOME/.bashrc"

echo "Uninstall complete. Reboot if wlan0 or NetworkManager state needs a full reset."
