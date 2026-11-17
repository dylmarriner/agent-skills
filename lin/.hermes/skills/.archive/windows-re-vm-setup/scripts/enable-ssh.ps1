# Enable-OpenSSH.ps1
# Run this in an Admin PowerShell inside the Windows VM to enable SSH access.
# This does NOT require keyboard injection from host — run it from SPICE or local desktop.
#
# Usage:
#   Right-click Start → PowerShell (Admin) → paste and Enter
#   Or: powershell -ExecutionPolicy Bypass -File .\enable-ssh.ps1

Write-Host "[1/4] Installing OpenSSH Server..." -ForegroundColor Cyan
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

Write-Host "[2/4] Starting SSH service..." -ForegroundColor Cyan
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'

Write-Host "[3/4] Adding firewall rule..." -ForegroundColor Cyan
New-NetFirewallRule -Name 'OpenSSH-Server' -DisplayName 'OpenSSH Server (SSH)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22

Write-Host "[4/4] Verifying..." -ForegroundColor Cyan
Get-Service sshd | Format-Table Name, Status, StartType
Get-NetFirewallRule -Name 'OpenSSH-Server' | Format-Table Name, Enabled, Action

Write-Host ""
Write-Host "SSH server ready." -ForegroundColor Green
Write-Host "Connect from any Tailscale peer: ssh re@100.x.x.x" -ForegroundColor Yellow
