@echo off
echo Requesting administrator privileges to set Ethernet 2 metric to 500...
powershell -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -Command Set-NetIPInterface -InterfaceAlias \"Ethernet 2\" -InterfaceMetric 500; Write-Host \"[SUCCESS] Ethernet 2 metric set to 500!\"; Write-Host \"Your PC will now use your home Wi-Fi for Internet and Ethernet 2 for CSI sensing simultaneously.\"; Start-Sleep -Seconds 3'"
echo Launched elevation request.
