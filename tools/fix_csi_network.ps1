# Run this in an Administrator PowerShell prompt
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "[*] Configuring Ethernet 2 for CSI Studio..." -ForegroundColor Yellow

# 1. Assign static IP 192.168.2.2 with NO default gateway (keeps Internet on Wi-Fi)
netsh interface ipv4 set address name="Ethernet 2" static 192.168.2.2 255.255.255.0 none

# 2. Set interface metric to 500 (lower priority than Wi-Fi)
netsh interface ipv4 set interface "Ethernet 2" metric=500

# 3. Disable Realtek Green Ethernet / Energy-Efficient Ethernet / Power Saving
Set-NetAdapterAdvancedProperty -Name "Ethernet 2" -DisplayName "Energy-Efficient Ethernet" -DisplayValue "Disabled" -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name "Ethernet 2" -DisplayName "Green Ethernet" -DisplayValue "Disabled" -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name "Ethernet 2" -DisplayName "Power Saving Mode" -DisplayValue "Disabled" -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name "Ethernet 2" -DisplayName "Gigabit Lite" -DisplayValue "Disabled" -ErrorAction SilentlyContinue
Set-NetAdapterAdvancedProperty -Name "Ethernet 2" -DisplayName "Speed & Duplex" -DisplayValue "100 Mbps Full Duplex" -ErrorAction SilentlyContinue

# 4. Restart adapter to apply
Restart-NetAdapter -Name "Ethernet 2" -ErrorAction SilentlyContinue

Write-Host "`n[SUCCESS] Ethernet 2 fully configured:" -ForegroundColor Green
Write-Host " - Static IP: 192.168.2.2 (Subnet: 255.255.255.0)" -ForegroundColor White
Write-Host " - Gateway: None (Protects your home Wi-Fi Internet!)" -ForegroundColor White
Write-Host " - Metric: 500 (Wi-Fi stays primary for Internet)" -ForegroundColor White
Write-Host " - Green Ethernet & Power Saving: Disabled (No link drops!)" -ForegroundColor White
Write-Host " - Speed & Duplex: 100 Mbps Full Duplex" -ForegroundColor White
Write-Host "======================================================" -ForegroundColor Cyan
