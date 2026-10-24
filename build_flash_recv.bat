@echo off
set "IDF_TOOLS_PATH=E:\Espressif"
call "E:\Espressif\esp-idf\export.bat"
cd /d "E:\Vli\PROJECTS\Project 2 - wifi sensing\firmware\esp-csi\examples\get-started\csi_recv"
echo [*] Building csi_recv firmware...
idf.py build
echo [*] Flashing csi_recv firmware to Sabi Board (COM4)...
idf.py -p COM4 flash
