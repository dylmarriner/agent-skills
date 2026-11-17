# usb-presence.ps1 — ground-truth check: is the target phone REALLY on this host's USB bus right now?
# Unlike `pnputil /enum-devices` and bare `Get-PnpDevice`, this filters by the `Present` flag so
# ghost/cached driver nodes (stored VID:PID + COM ports from previous plugs) do NOT false-positive.
#
# Usage over SSH (normalize the target VID filter to your device):
#   powershell -ExecutionPolicy Bypass -File usb-presence.ps1
# Run it on the Windows host, or stage+copy there and invoke via ssh.

$vidFilter = if ($args.Count -gt 0) { $args[0] } else { 'USB*VID_04E8*' }   # default Samsung

Write-Host "=== PRESENT devices matching $vidFilter ==="
$present = Get-PnpDevice | Where-Object { $_.Present -and $_.InstanceId -like $vidFilter }
if ($present) { $present | Format-List Status, FriendlyName, InstanceId } else { Write-Host "(none present)" }

Write-Host "=== PRESENT USB/Ports class count (sanity) ==="
(Get-PnpDevice | Where-Object { $_.Present -and $_.Class -in @('USB','Ports','WPD','Modem') }).Count

Write-Host "=== LIVE COM PORTS (a present download-mode phone has one) ==="
$ports = [System.IO.Ports.SerialPort]::GetPortNames()
if ($ports) { $ports } else { Write-Host "(no live COM ports)" }

Write-Host "=== GHOST proof: bare Get-PnpDevice hits vs Present (expect ghosts when phone is unplugged) ==="
$all  = Get-PnpDevice | Where-Object { $_.InstanceId -like $vidFilter }
$np   = $all | Where-Object { -not $_.Present }
Write-Host ("VID{0} total={1} present={2} GHOST={3}" -f $vidFilter, $all.Count, $present.Count, $np.Count)

# Interpretation:
#   present.Count -eq 0 AND live COM ports empty  -> phone NOT on the bus. It is either unplugged,
#     on a charge-only cable, on a hub/charger, or on this host but with no data path. "Turned on"
#     alone does NOT put it on the bus.
#   Samsung mode discriminator: PID 6860 = normal booted (MTP/composite); PID 685D = download mode
#     (a live COM port appears). Both ghost as stored nodes when pulled, so Present is the arbiter.