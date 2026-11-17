# Pi 5 Optimization Targets

Common resource-heavy services to disable/remove when optimizing a Pi 5:

## 1. Desktop Environment (Xfce)
Typical footprint: ~400MB RAM
```
apt purge -y --purge xfce4 xfce4-* lightdm lxde lxde-*
apt purge -y --purge lxappearance lxinput lxpanel lxrandr lxsession lxterminal pcmanfm
apt purge -y --purge xorg xserver-xorg-*
apt autoremove -y --purge
```

## 2. Dual Ad-Blockers
Pick one. Having both Pi-hole + AdGuardHome wastes 200-400MB:
```bash
# Pi-hole — the interactive "pihole uninstall" may prompt and cancel.
# Use the non-interactive approach instead:
sudo DEBIAN_FRONTEND=noninteractive apt purge -y --purge pihole-meta
sudo systemctl stop pihole-FTL
sudo systemctl disable pihole-FTL
sudo rm -f /etc/systemd/system/pihole-FTL.service
sudo rm -rf /etc/pihole /opt/pihole /usr/local/bin/pihole /var/log/pihole*
sudo deluser pihole 2>/dev/null || true
sudo systemctl daemon-reload

# AdGuardHome
sudo systemctl stop AdGuardHome && sudo systemctl disable AdGuardHome
sudo rm -rf /opt/AdGuardHome
sudo deluser adguardhome
```

## 3. Ollama (Local LLM serving)
```
systemctl stop ollama && systemctl disable ollama
rm -f /usr/local/bin/ollama /usr/bin/ollama
rm -rf /usr/share/ollama /etc/ollama
```

## 4. LiteLLM (LLM proxy)
```
pkill -f litellm
systemctl stop litellm 2>/dev/null && systemctl disable litellm 2>/dev/null
rm -rf /home/*/.local/share/litellm-venv
pip3 uninstall -y litellm
```

## 5. Heavy Monitoring Stack (Grafana + Prometheus + Alloy + Loki)
~643MB combined. Consider simplifying if overkill for a Pi:
- Prometheus + Node Exporter alone is ~150MB
- Adding Grafana pushes it to ~400MB
- Alloy + Loki adds another ~250MB

## 6. RustDesk (Remote desktop)
~100MB — unneeded if SSH is the access method.

## 7. Suricata (IDS)
CPU-intensive packet inspection. Disable if network security isn't critical.
