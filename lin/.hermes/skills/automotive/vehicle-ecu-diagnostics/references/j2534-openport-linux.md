# Tactrix OpenPort 2.0 (and J2534 passthru) on Linux

## Identify the adapter

```bash
lsusb                                  # expect 0403:cc4d  Future Technology Devices Intl. OpenPort 2.0
for f in idVendor idProduct product manufacturer serial; do echo "$f=$(cat /sys/bus/usb/devices/1-1/$f)"; done
dmesg | tail -20                       # 'new full-speed USB device' + 'cdc_acm ... ttyACM0'
ls -l /dev/bus/usb/001/036             # 660 root:plugdev when the udev rule is present
```

Udev rule that gives the operator access (group membership in `plugdev` or `dialout` matters):

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="cc4d", MODE="0660", GROUP="plugdev", TAG+="uaccess"
```

## Free the interface for libusb

The passthru driver claims the raw device through libusb. If the kernel already bound `cdc_acm`
(the usual Linux default for this hardware, giving `/dev/ttyACM0`) the J2534 layer cannot take the
interface:

```bash
sudo sh -c 'echo -n "1-1:1.0" > /sys/bus/usb/drivers/cdc_acm/unbind'   # before opening a J2534 session
sudo sh -c 'echo -n "1-1:1.0" > /sys/bus/usb/drivers/cdc_acm/bind'     # afterwards, to get ttyACM0 back
```

Check binding with:

```bash
for i in /sys/bus/usb/devices/1-1/1-1:*; do echo "$(basename $i) driver=$(basename $(readlink $i/driver 2>/dev/null))" ; done
```

An empty `driver=` on every interface means the device is free for libusb. Binding the second
interface of an ACM pair fails with `No such device` — that is normal, the data interface follows the
control one. Never bind/unbind while a session is open.

## Driver

The open-source Linux passthru shim (NikolaKozina/j2534) builds against libusb-1.0-dev and is the
usual bundled artifact (`drivers/linux/j2534.so`); projects often expose it via
`MUTS_J2534_LIBRARY` or an equivalent env var. Verify it loads and that the firmware handshake
returns a version — a wrapper that insists on a real firmware string is your friend, an empty one
often means the interface is still kernel-owned:

```
PassThruReadVersion ->  firmware 1.17.4877   dll 3.0.0 (libusb-1.0.29.11953)   api 04.04
```

`ctypes.CDLL(path)` on Linux, `ctypes.WinDLL` on Windows; the exported entry points are the
`PassThru*` family, and `nm -D --defined-only j2534.so` confirms them.

## ISO15765 message layout

- TX/RX frames put a **4-byte big-endian CAN ID prefix in front of the payload** in `PASSTHRU_MSG.Data`
  (`can_id >> 24 … can_id & 0xFF`, then the diagnostic bytes). The driver does ISO-TP segmentation,
  the application sees complete PDUs including negative responses.
- Received ISO15765 payloads can report `ProtocolID == 0` — accept `ProtocolID in (ISO15765, 0)`.
- Drop driver indications: `RxStatus & 0x0B` (TX echo `0x01`, start-of-message `0x02`, TX_DONE `0x08`)
  and anything with fewer than 5 data bytes.
- A `0x78` response-pending inside `7F <sid> 78` is consumed while waiting for the real answer, not
  returned to the caller.

## Channels, filters, configuration

- Connect with protocol ISO15765, the bus baud (500000 on most CAN vehicles), and a
  `FLOW_CONTROL_FILTER` built from mask `0x7FF`, pattern = response ID, flow control = request ID.
  Consequence: **one channel sees one module** — to inventory modules, reconnect per
  `0x7E0+i`/`0x7E8+i` pair rather than expecting a broadcast to collect multiple responders.
- Block size / STmin go through `SET_CONFIG` (`ISO15765_BS` `0x1E`, `ISO15765_STMIN` `0x1F`).
- K-line (ISO 9141 / ISO 14230) is a different connect path with a zero-mask `PASS_FILTER` and a
  5-baud init that returns two key bytes; do not mix the two config paths.
- Frame padding matters on some modules — pad to 8 bytes when the ECU ignores unpadded single frames.

## Failure reading

| symptom | first thing to check |
|---|---|
| `PassThruOpen` / firmware handshake fails | interface still bound to `cdc_acm`/`ftdi_sio`, or no read/write on `/dev/bus/usb/BBB/DDD` |
| opens, then every request times out | wrong baud, ignition/bus power, wrong ID pair, or terminator/bench wiring |
| echo frames only, no ECU data | filter pattern wrong (must be the response ID) |
| `PassThruReadMsgs` returns timeout codes | treat as empty result, not an error; distinguish from a real driver error |
