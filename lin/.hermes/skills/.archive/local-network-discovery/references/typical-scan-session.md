# Typical Scan Session — Spark Router Subnet

From a session on 2026-07-15 discovering a Sony device on a Spark NZ network.

## Context

- Router: Spark NZ, 192.168.1.254
- Login: admin / custom password via web UI at http://192.168.1.254/login.htm
- Router web UI "Connected Devices" page showed empty tables for Ethernet, 2.4GHz, 5GHz — **not reliable**

## Scan Results

### arp-scan output

```
Interface: wlo1, type: EN10MB, MAC: 04:d3:b0:eb:35:25, IPv4: 192.168.1.248
Starting arp-scan 1.10.0 with 256 hosts
192.168.1.222  88:a2:9e:08:fb:0a  (Unknown)
192.168.1.225  1c:1b:0d:1d:0b:22  GIGA-BYTE TECHNOLOGY CO.,LTD.
192.168.1.230  c8:9e:43:98:b1:0f  NETGEAR
192.168.1.235  5c:84:3c:cb:6f:1f  Sony Interactive Entertainment Inc.
192.168.1.236  54:07:7d:32:6c:fb  NETGEAR
192.168.1.231  78:8b:2a:c6:cf:a2  Zhen Shi Information Technology (Shanghai) Co., Ltd.
192.168.1.239  e4:fa:c4:6d:45:69  (Unknown)
192.168.1.254  04:09:86:23:b1:b9  (Unknown)
192.168.1.72   8c:c8:4b:1c:da:67  CHONGQING FUGUI ELECTRONICS CO.,LTD.
192.168.1.228  7c:01:3e:91:9c:d2  (Unknown)
192.168.1.227  4c:c9:5e:7c:79:1d  Samsung Electronics Co.,Ltd
192.168.1.232  78:28:ca:5b:0f:94  Sonos, Inc.
192.168.1.233  78:28:ca:5b:0f:94  Sonos, Inc.
192.168.1.241  88:41:fc:90:38:22  AirTies Wireless Networks
192.168.1.244  88:41:fc:90:38:22  AirTies Wireless Networks
192.168.1.247  10:94:bb:d4:ef:90  Apple, Inc.
```

### Sony Device Identification

- IP: 192.168.1.235
- MAC: 5c:84:3c:cb:6f:1f — Sony Interactive Entertainment Inc.
- Open port: 9295 (PlayStation Remote Play protocol)
- Confirmed: PlayStation (PS4/PS5 class device)
- nmap SYN scan timed out against this device — had to use `nc -zv -w 1` for port probing

### Device Notes

- **Spark AirTies** (.241/.244, same MAC): The router's own WiFi mesh extenders, not actual clients
- **Sonos** (.232/.233, same MAC): Same physical Sonos device with wired + wireless interface
- **Host machine** (.248): This device running the scan (MAC 04:d3:b0:eb:35:25)
- 2 Samsung devices (.222, .227, .239) — mobiles/tablets
