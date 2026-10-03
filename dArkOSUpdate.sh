#!/bin/bash

clear
UPDATE_DATE="10032026"
LOG_FILE="/home/ark/update$UPDATE_DATE.log"
BASE_UPDATE_DONE="/home/ark/.config/.update$UPDATE_DATE"
PATCH_UPDATE_DONE="/home/ark/.config/.update10032026-r1"
if [ -f "$BASE_UPDATE_DONE" ]; then
	UPDATE_DONE="$PATCH_UPDATE_DONE"
else
	UPDATE_DONE="$BASE_UPDATE_DONE"
fi

if [ -f "$UPDATE_DONE" ] || [ -z "$UPDATE_DONE" ]; then
	msgbox "No more updates available.  Check back later."
	rm -- "$0"
	exit 187
fi

if [ -f "$LOG_FILE" ]; then
	sudo rm "$LOG_FILE"
fi

LOCATION="https://raw.githubusercontent.com/dixtuel/darkos-updates/main"

c_brightness="$(cat /sys/class/backlight/backlight/brightness)"
sudo chmod 666 /dev/tty1
echo 255 > /sys/class/backlight/backlight/brightness
touch $LOG_FILE
tail -f $LOG_FILE >> /dev/tty1 &

if [ ! -f "/home/ark/.config/.update12242025" ]; then

	printf "\nAdd missing files for Drastic\nUpdate drastic.sh script\n" | tee -a "$LOG_FILE"
	sudo rm -rf /dev/shm/*
	sudo wget -t 3 -T 60 --no-check-certificate "$LOCATION"/12242025/darkosupdate12242025.zip -O /dev/shm/darkosupdate12242025.zip -a "$LOG_FILE" || sudo rm -f /dev/shm/darkosupdate12242025.zip | tee -a "$LOG_FILE"
	if [ -f "/dev/shm/darkosupdate12242025.zip" ]; then
	  sudo unzip -X -o /dev/shm/darkosupdate12242025.zip -d / | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate12242025.zip | tee -a "$LOG_FILE"
	else
	  printf "\nThe update couldn't complete because the package did not download correctly.\nPlease retry the update again." | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate12242025.z* | tee -a "$LOG_FILE"
	  sleep 3
	  echo $c_brightness > /sys/class/backlight/backlight/brightness
	  exit 1
	fi

	printf "\nUpdate boot text to reflect current version of dArkOS\n" | tee -a "$LOG_FILE"
	sudo sed -i "/title\=/c\title\=dArkOS ($UPDATE_DATE)" /usr/share/plymouth/themes/text.plymouth
	echo "$UPDATE_DATE" > /home/ark/.config/.VERSION

	touch "/home/ark/.config/.update12242025"

fi

if [ ! -f "/home/ark/.config/.update12312025" ]; then

	printf "\nUpdate Emulationstation for chinese language based fixes and timezone updating\nFix Playstation not working with 32bit pcsx_rearmed cores\nFix controls for duckstation standalone emulator\nRevert osk.py\nFix checknswitchforusbdac\nFix no audio on boot for rgb10\n" | tee -a "$LOG_FILE"
	sudo rm -rf /dev/shm/*
	sudo wget -t 3 -T 60 --no-check-certificate "$LOCATION"/12312025/darkosupdate12312025.zip -O /dev/shm/darkosupdate12312025.zip -a "$LOG_FILE" || sudo rm -f /dev/shm/darkosupdate12312025.zip | tee -a "$LOG_FILE"
	if [ -f "/dev/shm/darkosupdate12312025.zip" ]; then
	  sudo unzip -X -o /dev/shm/darkosupdate12312025.zip -d / | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate12312025.zip | tee -a "$LOG_FILE"
	else
	  printf "\nThe update couldn't complete because the package did not download correctly.\nPlease retry the update again." | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate12312025.z* | tee -a "$LOG_FILE"
	  sleep 3
	  echo $c_brightness > /sys/class/backlight/backlight/brightness
	  exit 1
	fi

	printf "\nCopy correct pcsx_rearmed 32bit core depending on chipset\n" | tee -a "$LOG_FILE"
	if [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  rm -f /home/ark/.config/retroarch32/cores/pcsx_rearmed_libretro.so.rk3326
	  rm -f /home/ark/.config/retroarch32/cores/pcsx_rearmed_rumble_libretro.so.rk3326
	else
	  cp -f /home/ark/.config/retroarch32/cores/pcsx_rearmed_libretro.so.rk3326 /home/ark/.config/retroarch32/cores/pcsx_rearmed_libretro.so
	  cp -f /home/ark/.config/retroarch32/cores/pcsx_rearmed_rumble_libretro.so.rk3326 /home/ark/.config/retroarch32/cores/pcsx_rearmed_rumble_libretro.so
	  rm -f /home/ark/.config/retroarch32/cores/pcsx_rearmed_libretro.so.rk3326
	  rm -f /home/ark/.config/retroarch32/cores/pcsx_rearmed_rumble_libretro.so.rk3326
	fi

	printf "\nCopy correct emulationstation depending on device\n" | tee -a "$LOG_FILE"
	if [ -f "/boot/rk3326-rg351mp-linux.dtb" ] || [ -f "/boot/rk3326-g350-linux.dtb" ]; then
	  sudo mv -fv /home/ark/emulationstation.351v /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	elif [ -f "/boot/rk3326-odroidgo2-linux.dtb" ] || [ -f "/boot/rk3326-odroidgo2-linux-v11.dtb" ] || [ -f "/boot/rk3326-odroidgo3-linux.dtb" ]; then
      sudo cp -fv /home/ark/emulationstation.header /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo cp -fv /home/ark/emulationstation.351v /usr/bin/emulationstation/emulationstation.fullscreen | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	else
	  sudo mv -fv /home/ark/emulationstation.503 /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	fi

	if [ -f "/boot/rk3326-odroidgo2-linux-v11.dtb" ]; then
	  printf "\nUpdate ogage\n" | tee -a "$LOG_FILE"
	  sudo mv -fv /home/ark/ogage /usr/local/bin/ogage | tee -a "$LOG_FILE"
	  sudo chmod 777 /usr/local/bin/ogage
	else
	  printf "\nNo need to update ogage\n" | tee -a "$LOG_FILE"
	  rm -fv /home/ark/ogage | tee -a "$LOG_FILE"
	fi

	printf "\nAdd BigPEmu to emulationstaton as the Atari Jagauar emulator.  Forget about the retroarch core.\n" | tee -a "$LOG_FILE"
	cp -v /etc/emulationstation/es_systems.cfg /etc/emulationstation/es_systems.cfg.update12312025.bak
	sed -i 's|/usr/local/bin/retroarch -L /home/ark/.config/retroarch/cores/virtualjaguar_libretro\.so|/usr/local/bin/bigpemu.sh|g' /etc/emulationstation/es_systems.cfg
	mkdir -p /roms/atarijaguar
	if test ! -z "$(cat /etc/fstab | grep roms2 | tr -d '\0')"
	then
	  mkdir -p /roms2/atarijaguar
	fi

	printf "\nAdd mediatek firmware files, ntfs support, and vlc\n" | tee -a "$LOG_FILE"
	sudo apt update -y  | tee -a "$LOG_FILE"
	sudo apt -y install firmware-mediatek ntfs-3g vlc-data vlc-plugin-base | tee -a "$LOG_FILE"

	printf "\nInstall libavcodec58 for portmaster\n" | tee -a "$LOG_FILE"
	wget -t 3 -T 60 --no-check-certificate http://security.debian.org/debian-security/pool/updates/main/f/ffmpeg/libavcodec58_4.3.9-0+deb11u1_arm64.deb | tee -a "$LOG_FILE"
	dpkg --fsys-tarfile libavcodec58_4.3.9-0+deb11u1_arm64.deb | tar -xO ./usr/lib/aarch64-linux-gnu/libavcodec.so.58.91.100 > libavcodec.so.58
	sudo mv -f libavcodec.so.58 /usr/lib/aarch64-linux-gnu/
	sudo chown root:root /usr/lib/aarch64-linux-gnu/libavcodec.so.58
	rm -f libavcodec58_4.3.9-0+deb11u1_arm64.deb
    wget -t 3 -T 60 --no-check-certificate http://security.debian.org/debian-security/pool/updates/main/f/ffmpeg/libavcodec58_4.3.9-0+deb11u1_armhf.deb | tee -a "$LOG_FILE"
	dpkg --fsys-tarfile libavcodec58_4.3.9-0+deb11u1_armhf.deb | tar -xO ./usr/lib/arm-linux-gnueabihf/libavcodec.so.58.91.100 > libavcodec.so.58
	sudo mv -f libavcodec.so.58 /usr/lib/arm-linux-gnueabihf/
	sudo chown root:root /usr/lib/arm-linux-gnueabihf/libavcodec.so.58
	rm -f libavcodec58_4.3.9-0+deb11u1_armhf.deb

	printf "\nUpdate boot text to reflect current version of dArkOS\n" | tee -a "$LOG_FILE"
	sudo sed -i "/title\=/c\title\=dArkOS ($UPDATE_DATE)" /usr/share/plymouth/themes/text.plymouth
	echo "$UPDATE_DATE" > /home/ark/.config/.VERSION

	touch "/home/ark/.config/.update12312025"

fi

if [ ! -f "/home/ark/.config/.update01082026" ]; then

	printf "\nUpdate Emulationstation to fix swap ab when in options and crashing while scrolling with few games loaded\nUpdate emulationstation translations\nFix drastic in game saves and default restore for rg351mp\nAdd Vietnamese ES translation\nAdd Sharp Shimmerless Shader\nFix Chinese text rendering\nAdd liblcf library for easyrpg\nAdd missing easyrpg.sh script\nChange default j2me emulator to freej2me-plus\n" | tee -a "$LOG_FILE"
	sudo rm -rf /dev/shm/*
	sudo wget -t 3 -T 60 --no-check-certificate "$LOCATION"/01082026/darkosupdate01082026.zip -O /dev/shm/darkosupdate01082026.zip -a "$LOG_FILE" || sudo rm -f /dev/shm/darkosupdate01082026.zip | tee -a "$LOG_FILE"
	if [ -f "/dev/shm/darkosupdate01082026.zip" ]; then
	  sudo unzip -X -o /dev/shm/darkosupdate01082026.zip -d / | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate01082026.zip | tee -a "$LOG_FILE"
	else
	  printf "\nThe update couldn't complete because the package did not download correctly.\nPlease retry the update again." | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate01082026.z* | tee -a "$LOG_FILE"
	  sleep 3
	  echo $c_brightness > /sys/class/backlight/backlight/brightness
	  exit 1
	fi

	printf "\nCopy correct emulationstation depending on device\n" | tee -a "$LOG_FILE"
	if [ -f "/boot/rk3326-rg351mp-linux.dtb" ] || [ -f "/boot/rk3326-g350-linux.dtb" ]; then
	  sudo mv -fv /home/ark/emulationstation.351v /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	elif [ -f "/boot/rk3326-odroidgo2-linux.dtb" ] || [ -f "/boot/rk3326-odroidgo2-linux-v11.dtb" ] || [ -f "/boot/rk3326-odroidgo3-linux.dtb" ]; then
      sudo cp -fv /home/ark/emulationstation.header /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo cp -fv /home/ark/emulationstation.351v /usr/bin/emulationstation/emulationstation.fullscreen | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	else
	  sudo mv -fv /home/ark/emulationstation.503 /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	fi

	printf "\nCopy correct emulationstation settings depending on chipset\n" | tee -a "$LOG_FILE"
	cp -v /etc/emulationstation/es_systems.cfg /etc/emulationstation/es_systems.cfg.update01082026.bak
	if [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  cp -f /etc/emulationstation/es_systems.cfg.rk3566 /etc/emulationstation/es_systems.cfg
	  rm -f /etc/emulationstation/es_systems.cfg.rk*
	else
	  cp -f /etc/emulationstation/es_systems.cfg.rk3326 /etc/emulationstation/es_systems.cfg
	  rm -f /etc/emulationstation/es_systems.cfg.rk*
	fi
	if test ! -z "$(cat /etc/fstab | grep roms2 | tr -d '\0')"
	then
 	  printf "\nAccomodate for roms2 with new es_systems.cfg file...\n" | tee -a "$LOG_FILE"
	  sed -i '/<path>\/roms\//s//<path>\/roms2\//g' /etc/emulationstation/es_systems.cfg
	fi

	if [ ! -z "$(grep "RGB30" /home/ark/.config/.DEVICE | tr -d '\0')" ] || [ ! -z "$(grep "RGB20PRO" /home/ark/.config/.DEVICE | tr -d '\0')" ]; then
	  printf "\nUpdate batt_life_warning.py script\n" | tee -a "$LOG_FILE"
	  sudo cp -fv /home/ark/powkiddy/batt_life_warning.py /usr/local/bin/. | tee -a "$LOG_FILE"
	elif [ ! -z "$(grep "RG351MP" /home/ark/.config/.DEVICE | tr -d '\0')" ]; then
	  printf "\nUpdate batt_life_warning.py scripts\n" | tee -a "$LOG_FILE"
	  sudo cp -fv /home/ark/rg351mp/batt_life_warning.py* /usr/local/bin/. | tee -a "$LOG_FILE"
	fi
	rm -rfv /home/ark/powkiddy/ | tee -a "$LOG_FILE"
	rm -rfv /home/ark/rg351mp/ | tee -a "$LOG_FILE"

	printf "\nRemove Backup ArkOS and Restore ArkOS settings scripts.  They're now replaced with Backup dArkOS and Restore dArkOS settings scripts\n" | tee -a "$LOG_FILE"
	rm -fv /opt/system/Advanced/Backup\ ArkOS\ Settings.sh | tee -a "$LOG_FILE"
	rm -fv /opt/system/Advanced/Restore\ ArkOS\ Settings.sh | tee -a "$LOG_FILE"

	printf "\nMove bigpemu defaultconfig to defaultconfigs\n"
	mv -v /opt/bigpemu/defaultconfig/ /opt/bigpemu/defaultconfigs/ | tee -a "$LOG_FILE"

	printf "\nMove Scan_for_new_games.alg from scummvm to alg\n"
	mv -v /roms/scummvm/Scan_for_new_games.alg /roms/alg/Scan_for_new_games.alg | tee -a "$LOG_FILE"
	if test ! -z "$(cat /etc/fstab | grep roms2 | tr -d '\0')"
	then
	  mv -v /roms2/scummvm/Scan_for_new_games.alg /roms2/alg/Scan_for_new_games.alg | tee -a "$LOG_FILE"
	fi

	printf "\nAdd netcat for online download of j2me\n" | tee -a "$LOG_FILE"
	sudo apt update -y  | tee -a "$LOG_FILE"
	sudo apt -y install netcat-openbsd | tee -a "$LOG_FILE"

	printf "\nUpdate boot text to reflect current version of dArkOS\n" | tee -a "$LOG_FILE"
	sudo sed -i "/title\=/c\title\=dArkOS ($UPDATE_DATE)" /usr/share/plymouth/themes/text.plymouth
	echo "$UPDATE_DATE" > /home/ark/.config/.VERSION

	touch "/home/ark/.config/.update01082026"

fi

if [ ! -f "/home/ark/.config/.update01162026" ]; then

	printf "\nFix Quick Mode\nFix OpenBOR\n" | tee -a "$LOG_FILE"
	sudo rm -rf /dev/shm/*
	sudo wget -t 3 -T 60 --no-check-certificate "$LOCATION"/01162026/darkosupdate01162026.zip -O /dev/shm/darkosupdate01162026.zip -a "$LOG_FILE" || sudo rm -f /dev/shm/darkosupdate01162026.zip | tee -a "$LOG_FILE"
	if [ -f "/dev/shm/darkosupdate01162026.zip" ]; then
	  sudo unzip -X -o /dev/shm/darkosupdate01162026.zip -d / | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate01162026.zip | tee -a "$LOG_FILE"
	else
	  printf "\nThe update couldn't complete because the package did not download correctly.\nPlease retry the update again." | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate01162026.z* | tee -a "$LOG_FILE"
	  sleep 3
	  echo $c_brightness > /sys/class/backlight/backlight/brightness
	  exit 1
	fi

	if [ -f "/opt/system/Advanced/Enable Quick Mode.sh" ]; then
	  sudo rm -fv /usr/local/bin/quickmode.sh | tee -a "$LOG_FILE"
	fi

	if [ ! -f "/etc/polkit-1/rules.d/10-networkmanager.rules" ]; then
	  printf "\nRemove requirement for sudo to control nmcli\n" | tee -a "$LOG_FILE"
	  cat <<EOF | sudo tee /etc/polkit-1/rules.d/10-networkmanager.rules
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager") == 0 &&
        subject.isInGroup("netdev")) {
        return polkit.Result.YES;
    }
});
EOF
	fi

	if [ ! -z "$(grep "RG353" /home/ark/.config/.DEVICE | tr -d '\0')" ] && [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  printf "\nFix unknown panel version info for RG353V/VS and RG353M V1 and V2 units\n" | tee -a "$LOG_FILE"
	  sudo dd if=/home/ark/resource.img of=/dev/mmcblk1 bs=512 seek=24576 conv=notrunc | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/resource.img | tee -a "$LOG_FILE"
	else
	  sudo rm -fv /home/ark/resource.img | tee -a "$LOG_FILE"
	fi

	printf "\nUpgraded Debian Trixie OS to version 13.3\n" | tee -a "$LOG_FILE"
	sudo apt -y update | tee -a "$LOG_FILE"
	sudo apt -y upgrade | tee -a "$LOG_FILE"

	printf "\nUpdate boot text to reflect current version of dArkOS\n" | tee -a "$LOG_FILE"
	sudo sed -i "/title\=/c\title\=dArkOS ($UPDATE_DATE)" /usr/share/plymouth/themes/text.plymouth
	echo "$UPDATE_DATE" > /home/ark/.config/.VERSION

	touch "/home/ark/.config/.update01162026"

fi

if [ ! -f "/home/ark/.config/.update01302026" ]; then

	printf "\nAdd gif and vid option to emulationstation\nFix perfmax and perfnorm scripts\nFix hdmi-test script\nUpdate local netplay based scripts and configs\n" | tee -a "$LOG_FILE"
	sudo rm -rf /dev/shm/*
	sudo wget -t 3 -T 60 --no-check-certificate "$LOCATION"/01302026/darkosupdate01302026.zip -O /dev/shm/darkosupdate01302026.zip -a "$LOG_FILE" || sudo rm -f /dev/shm/darkosupdate01302026.zip | tee -a "$LOG_FILE"
	if [ -f "/dev/shm/darkosupdate01302026.zip" ]; then
	  sudo unzip -X -o /dev/shm/darkosupdate01302026.zip -d / | tee -a "$LOG_FILE"
	  sudo cp -fv /opt/system/Advanced/Switch\ to\ SD2\ for\ Roms.sh /usr/local/bin/. | tee -a "$LOG_FILE"
	  if test ! -z "$(cat /etc/fstab | grep roms2 | tr -d '\0')"
	  then
	    sudo rm -fv /opt/system/Advanced/Switch\ to\ SD2\ for\ Roms.sh | tee -a "$LOG_FILE"
	  fi
	  if [ ! -z "$(grep "RGB10" /home/ark/.config/.DEVICE | tr -d '\0')" ]; then
	    sudo rm -fv /usr/local/bin/Switch\ to\ SD2\ for\ Roms.sh | tee -a "$LOG_FILE"
	  fi
	  sudo rm -fv /dev/shm/darkosupdate01302026.zip | tee -a "$LOG_FILE"
	else
	  printf "\nThe update couldn't complete because the package did not download correctly.\nPlease retry the update again." | tee -a "$LOG_FILE"
	  sudo rm -fv /dev/shm/darkosupdate01302026.z* | tee -a "$LOG_FILE"
	  sleep 3
	  echo $c_brightness > /sys/class/backlight/backlight/brightness
	  exit 1
	fi

	printf "\nAdd hostapd and dnsmasq for local netplay\n" | tee -a "$LOG_FILE"
	sudo apt update -y  | tee -a "$LOG_FILE"
	sudo mv -fv /etc/dnsmasq.conf /tmp/. | tee -a "$LOG_FILE"
	sudo mv -fv /etc/hostapd/hostapd.conf /tmp/. | tee -a "$LOG_FILE"
	sudo apt -y install hostapd dnsmasq | tee -a "$LOG_FILE"
	sudo mv -fv /tmp/dnsmasq.conf /etc/dnsmasq.conf | tee -a "$LOG_FILE"
	sudo mv -fv /tmp/hostapd.conf /etc/hostapd/hostapd.conf | tee -a "$LOG_FILE"
	sudo systemctl disable hostapd dnsmasq | tee -a "$LOG_FILE"

	if [[ "$(tr -d '\0' < /proc/device-tree/compatible)" != *"rk3566"* ]]; then
	  sudo rm -fv /usr/local/bin/hdmi-test.sh | tee -a "$LOG_FILE"
	fi

	sudo chown -R ark:ark /opt
	if [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  rm -fv /opt/gametank/GameTankEmulator.rk3326 | tee -a "$LOG_FILE"
	else
	  mv -fv /opt/gametank/GameTankEmulator.rk3326 /opt/gametank/GameTankEmulator | tee -a "$LOG_FILE"
	fi

	if [ ! -f "/usr/share/alsa/alsa.conf.mednafen" ]; then
	  printf "\nCreate missing alsa.conf.mednafen\n" | tee -a "$LOG_FILE"
	  sudo cp -fv /usr/share/alsa/alsa.conf /usr/share/alsa/alsa.conf.mednafen | tee -a "$LOG_FILE"
	  sudo sed -i '/\"\~\/.asoundrc\"/s//\"\~\/.asoundrc.mednafen\"/' /usr/share/alsa/alsa.conf.mednafen
	fi

	printf "\nCopy correct emulationstation settings depending on chipset\n" | tee -a "$LOG_FILE"
	cp -v /etc/emulationstation/es_systems.cfg /etc/emulationstation/es_systems.cfg.update01302026.bak
	if [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  cp -f /etc/emulationstation/es_systems.cfg.rk3566 /etc/emulationstation/es_systems.cfg
	  rm -f /etc/emulationstation/es_systems.cfg.rk*
	else
	  cp -f /etc/emulationstation/es_systems.cfg.rk3326 /etc/emulationstation/es_systems.cfg
	  rm -f /etc/emulationstation/es_systems.cfg.rk*
	fi
	mkdir -p /roms/gametank
	if test ! -z "$(cat /etc/fstab | grep roms2 | tr -d '\0')"
	then
 	  printf "\nAccomodate for roms2 with new es_systems.cfg file...\n" | tee -a "$LOG_FILE"
	  sed -i '/<path>\/roms\//s//<path>\/roms2\//g' /etc/emulationstation/es_systems.cfg
	  mkdir -p /roms2/gametank
	fi

	printf "\nCopy correct emulationstation depending on device\n" | tee -a "$LOG_FILE"
	if [ -f "/boot/rk3326-a10mini-linux.dtb" ] || [ -f "/boot/rk3326-rg351mp-linux.dtb" ] || [ -f "/boot/rk3326-g350-linux.dtb" ]; then
	  sudo mv -fv /home/ark/emulationstation.351v /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	elif [ -f "/boot/rk3326-odroidgo2-linux.dtb" ] || [ -f "/boot/rk3326-odroidgo2-linux-v11.dtb" ] || [ -f "/boot/rk3326-odroidgo3-linux.dtb" ]; then
      sudo cp -fv /home/ark/emulationstation.header /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo cp -fv /home/ark/emulationstation.351v /usr/bin/emulationstation/emulationstation.fullscreen | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	else
	  sudo mv -fv /home/ark/emulationstation.503 /usr/bin/emulationstation/emulationstation | tee -a "$LOG_FILE"
	  sudo rm -fv /home/ark/emulationstation.* | tee -a "$LOG_FILE"
	  sudo chmod -v 777 /usr/bin/emulationstation/emulationstation* | tee -a "$LOG_FILE"
	fi

	if [ ! -z "$(grep "A10MINI" /home/ark/.config/.DEVICE | tr -d '\0')" ]; then
	  printf "\nEnabling additional lower scaling frequencies for the A10 Mini power savings..\n" | tee -a "$LOG_FILE"
	  sudo cp -fv /home/ark/rk3326-a10mini-linux.dtb /boot/. | tee -a "$LOG_FILE"
	elif [ ! -z "$(grep "RG351MP" /home/ark/.config/.DEVICE | tr -d '\0')" ]; then
	  printf "\nEnabling additional lower scaling frequencies for the RG351MP power savings..\n" | tee -a "$LOG_FILE"
	  sudo cp -fv /home/ark/rk3326-rg351mp-linux.dtb /boot/. | tee -a "$LOG_FILE"
	fi
	sudo rm -fv /home/ark/rk3326-a10mini-linux.dtb /home/ark/rk3326-rg351mp-linux.dtb | tee -a "$LOG_FILE"

	printf "\nDoing some theme updates..\n\n" | tee -a "$LOG_FILE"
	for theme in es-theme-nes-box es-theme-sagabox es-theme-saganx es-theme-switch
	do
	  if [ -d "/roms/themes/$theme" ]; then
		printf "\nUpdating $theme\n" | tee -a "$LOG_FILE"
		cd /roms/themes/$theme
		git fetch origin
		git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)
		git pull
		cd /home/ark
	  fi
	done

	if [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  printf "\nAdd shutdown tasks for remembering panel settings\n" | tee -a "$LOG_FILE"
	  echo "@reboot /usr/local/bin/panel_set.sh RestoreSettings &" | sudo tee -a /var/spool/cron/crontabs/root
	  sudo systemctl daemon-reload
	  sudo systemctl enable shutdowntasks
	  sudo systemctl restart shutdowntasks
	else
	  sudo rm -fv /etc/systemd/system/shutdowntasks.service | tee -a "$LOG_FILE"
	  sudo rm -fv /usr/local/bin/panel_set.sh | tee -a "$LOG_FILE"
	fi

	if [ ! -z "$(grep "RG353V" /home/ark/.config/.DEVICE | tr -d '\0')" ] && [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  printf "\nRevert RG353V v2 screen changes from last update..\n" | tee -a "$LOG_FILE"
	  sudo mv -fv /home/ark/rk3566-353v.dtb /boot/. | tee -a "$LOG_FILE"
	  sudo mv -fv /home/ark/rk3566-353v-notimingchange.dtb /boot/. | tee -a "$LOG_FILE"
	elif [ ! -z "$(grep "RG353M" /home/ark/.config/.DEVICE | tr -d '\0')" ] && [[ "$(tr -d '\0' < /proc/device-tree/compatible)" == *"rk3566"* ]]; then
	  printf "\nAdd additonal notimingchange dtb to boot partition..\n" | tee -a "$LOG_FILE"
	  sudo mv -fv /home/ark/rk3566-353m-notimingchange.dtb /boot/. | tee -a "$LOG_FILE"
	fi
	sudo rm -fv /home/ark/rk3566-353* | tee -a "$LOG_FILE"

	printf "\nUpdate boot text to reflect current version of dArkOS\n" | tee -a "$LOG_FILE"
	sudo sed -i "/title\=/c\title\=dArkOSRE ($UPDATE_DATE)" /usr/share/plymouth/themes/text.plymouth
	echo "$UPDATE_DATE" > /home/ark/.config/.VERSION

	touch "$UPDATE_DONE"
	rm -v -- "$0" | tee -a "$LOG_FILE"
	printf "\033c" >> /dev/tty1
	msgbox "Updates have been completed.  System will now restart after you hit the A button to continue.  If the system doesn't restart after pressing A, just restart the system manually."
	echo $c_brightness > /sys/class/backlight/backlight/brightness
	sudo reboot
	exit 187

fi

# R36/R36S RK3326 focused update. This payload deliberately contains no ROM
# roots, EmulationStation system config, SD switching scripts, or game data.
if [ ! -f "/home/ark/.config/.update10032026" ]; then

  BASE_VERSION="$(cat /home/ark/.config/.VERSION 2>/dev/null)"
  if [[ "$(tr -d '\0' < /proc/device-tree/compatible 2>/dev/null)" != *"rk3326"* ]] || [ "$BASE_VERSION" != "03082026" ]; then
    printf "\nThis package requires dArkOSRE-R36 RK3326 firmware 03082026; no files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  fi

  printf "\nInstall verified RK3326 emulator/core updates while preserving the selected ROM card...\n" | tee -a "$LOG_FILE"

  UPDATE_ZIP="/dev/shm/darkosupdate10032026.zip"
  UPDATE_STAGE="/tmp/darkos-update10032026.$$"
  UPDATE_URL="$LOCATION/10032026/darkosupdate10032026.zip"
  UPDATE_SHA256="59df7021e908336fa8c7aee78c91bbf6beb8debdfada8af3e22588ff4324adba"

  if mountpoint -q /roms2; then
    ROM_ROOT="roms2"
    BACKUP_BASE="/roms2/backup/darkosre-update/10032026"
  else
    ROM_ROOT="roms"
    BACKUP_BASE="/roms/backup/darkosre-update/10032026"
  fi

  PATH_GUARD_BEFORE="$(sha256sum /etc/emulationstation/es_systems.cfg \
    "/usr/local/bin/Switch to SD2 for Roms.sh" \
    "/usr/local/bin/Switch to Main SD for Roms.sh" 2>/dev/null)"
  PATH_GUARD_COUNT="$(printf '%s\n' "$PATH_GUARD_BEFORE" | sed '/^$/d' | wc -l)"
  if [ "$PATH_GUARD_COUNT" -ne 3 ] || ! grep -q "<path>/$ROM_ROOT/" /etc/emulationstation/es_systems.cfg; then
    printf "\nROM card selection could not be verified; update stopped without installing files.\n" | tee -a "$LOG_FILE"
    exit 1
  fi

  sudo mkdir -p "$BACKUP_BASE" || exit 1
  mkdir -p "$UPDATE_STAGE" || exit 1
  if ! sudo touch "$BACKUP_BASE/.write-test"; then
    printf "\nCould not create a rollback backup on the active ROM card.\n" | tee -a "$LOG_FILE"
    rm -rf "$UPDATE_STAGE"
    exit 1
  fi
  sudo rm -f "$BACKUP_BASE/.write-test"

  AVAILABLE_TMP_KB="$(df -Pk /tmp | awk 'NR==2 {print $4}')"
  AVAILABLE_ROOT_KB="$(df -Pk /opt | awk 'NR==2 {print $4}')"
  if [ "${AVAILABLE_TMP_KB:-0}" -lt 250000 ] || [ "${AVAILABLE_ROOT_KB:-0}" -lt 300000 ]; then
    printf "\nNot enough temporary or system storage; update stopped before installation.\n" | tee -a "$LOG_FILE"
    rm -rf "$UPDATE_STAGE"
    exit 1
  fi

  wget -t 3 -T 120 --no-check-certificate "$UPDATE_URL" -O "$UPDATE_ZIP" -a "$LOG_FILE" || {
    rm -f "$UPDATE_ZIP"
    rm -rf "$UPDATE_STAGE"
    printf "\nCould not download the update package.\n" | tee -a "$LOG_FILE"
    exit 1
  }
  echo "$UPDATE_SHA256  $UPDATE_ZIP" | sha256sum -c - || {
    rm -f "$UPDATE_ZIP"
    rm -rf "$UPDATE_STAGE"
    printf "\nUpdate archive checksum did not match; no files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  }
  unzip -t "$UPDATE_ZIP" >/dev/null || {
    rm -f "$UPDATE_ZIP"
    rm -rf "$UPDATE_STAGE"
    printf "\nUpdate archive validation failed; no files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  }
  if unzip -Z1 "$UPDATE_ZIP" | grep -Eq '^(etc/emulationstation/es_systems.cfg|usr/local/bin/Switch to (SD2|Main SD) for Roms.sh|opt/system/Advanced/Switch to (SD2|Main SD) for Roms.sh|roms/|roms2/)'; then
    rm -f "$UPDATE_ZIP"
    rm -rf "$UPDATE_STAGE"
    printf "\nUpdate archive contains a ROM-root or SD-switch path; installation refused.\n" | tee -a "$LOG_FILE"
    exit 1
  fi
  unzip -q -o "$UPDATE_ZIP" -d "$UPDATE_STAGE" || {
    rm -f "$UPDATE_ZIP"
    rm -rf "$UPDATE_STAGE"
    printf "\nCould not stage update archive; no system files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  }

  UPDATE_PATHS=(
    "home/ark/.config/retroarch/cores/lowresnx_libretro.info"
    "home/ark/.config/retroarch/cores/lowresnx_libretro.so"
    "home/ark/.config/retroarch32/cores/parallel_n64_libretro.so"
    "opt/hypseus-singe/fonts"
    "opt/hypseus-singe/hypseus-singe"
    "opt/hypseus-singe/pics"
    "opt/ppsspp/PPSSPPSDL"
    "opt/ppsspp/assets"
    "opt/scummvm/scummvm"
    "opt/scummvm/themes"
    "opt/system/Update.sh"
    "opt/xroar/xroar"
    "usr/local/bin/retrorun"
    "usr/local/bin/retrorun32"
  )
  BACKUP_ARCHIVE="$BACKUP_BASE/rollback.tar"
  if [ ! -f "$BACKUP_BASE/backup-ready" ]; then
    sudo rm -rf "$BACKUP_BASE"
    sudo mkdir -p "$BACKUP_BASE" || exit 1
    printf '%s\n' "${UPDATE_PATHS[@]}" | sudo tee "$BACKUP_BASE/managed-paths.txt" >/dev/null
    sudo truncate -s 0 "$BACKUP_BASE/existed-paths.txt"
    EXISTED_PATHS=()
    for item in "${UPDATE_PATHS[@]}"; do
      if [ -e "/$item" ]; then
        EXISTED_PATHS+=("$item")
        printf '%s\n' "$item" | sudo tee -a "$BACKUP_BASE/existed-paths.txt" >/dev/null
      fi
    done
    if ((${#EXISTED_PATHS[@]})); then
      sudo tar --numeric-owner -cpf "$BACKUP_ARCHIVE.tmp" -C / -- "${EXISTED_PATHS[@]}" || {
        rm -f "$UPDATE_ZIP"
        rm -rf "$UPDATE_STAGE"
        printf "\nRollback archive creation failed; update stopped before installation.\n" | tee -a "$LOG_FILE"
        exit 1
      }
    else
      sudo tar -cpf "$BACKUP_ARCHIVE.tmp" --files-from=/dev/null || exit 1
    fi
    if ! sudo tar -tf "$BACKUP_ARCHIVE.tmp" >/dev/null; then
      rm -f "$UPDATE_ZIP"
      rm -rf "$UPDATE_STAGE"
      printf "\nRollback archive validation failed; update stopped before installation.\n" | tee -a "$LOG_FILE"
      exit 1
    fi
    sudo mv "$BACKUP_ARCHIVE.tmp" "$BACKUP_ARCHIVE" || exit 1
    sudo sha256sum "$BACKUP_ARCHIVE" | sudo tee "$BACKUP_BASE/rollback.sha256" >/dev/null
    sudo touch "$BACKUP_BASE/backup-ready"
  else
    if ! cmp -s <(printf '%s\n' "${UPDATE_PATHS[@]}") "$BACKUP_BASE/managed-paths.txt"; then
      printf "\nExisting rollback snapshot does not match this update; update stopped.\n" | tee -a "$LOG_FILE"
      rm -f "$UPDATE_ZIP"
      rm -rf "$UPDATE_STAGE"
      exit 1
    fi
    EXPECTED_BACKUP_SHA256="$(awk 'NR == 1 {print $1}' "$BACKUP_BASE/rollback.sha256" 2>/dev/null)"
    ACTUAL_BACKUP_SHA256="$(sha256sum "$BACKUP_ARCHIVE" 2>/dev/null | awk '{print $1}')"
    if [ -z "$EXPECTED_BACKUP_SHA256" ] || [ "$EXPECTED_BACKUP_SHA256" != "$ACTUAL_BACKUP_SHA256" ] || ! sudo tar -tf "$BACKUP_ARCHIVE" >/dev/null; then
      printf "\nRollback archive is missing or damaged; update stopped.\n" | tee -a "$LOG_FILE"
      rm -f "$UPDATE_ZIP"
      rm -rf "$UPDATE_STAGE"
      exit 1
    fi
  fi

  rollback_update() {
    printf "\nInstallation failed; restoring the previous files from $BACKUP_BASE\n" | tee -a "$LOG_FILE"
    ROLLBACK_FAILED=0
    for item in "${UPDATE_PATHS[@]}"; do
      sudo rm -rf "/$item" || ROLLBACK_FAILED=1
    done
    sudo tar --numeric-owner -xpf "$BACKUP_ARCHIVE" -C / || ROLLBACK_FAILED=1
    return "$ROLLBACK_FAILED"
  }

  for item in "${UPDATE_PATHS[@]}"; do
    if [ -e "$UPDATE_STAGE/$item" ]; then
      sudo mkdir -p "/$(dirname "$item")"
      if [ -d "$UPDATE_STAGE/$item" ]; then
        sudo rm -rf "/$item"
        sudo cp -a "$UPDATE_STAGE/$item" "/$(dirname "$item")/" || { rollback_update; exit 1; }
      else
        sudo install -m "$(stat -c '%a' "$UPDATE_STAGE/$item")" "$UPDATE_STAGE/$item" "/$item.new" || { rollback_update; exit 1; }
        sudo mv -f "/$item.new" "/$item" || { rollback_update; exit 1; }
      fi
    fi
  done

  PATH_GUARD_AFTER="$(sha256sum /etc/emulationstation/es_systems.cfg \
    "/usr/local/bin/Switch to SD2 for Roms.sh" \
    "/usr/local/bin/Switch to Main SD for Roms.sh" 2>/dev/null)"
  if [ "$PATH_GUARD_BEFORE" != "$PATH_GUARD_AFTER" ] || ! grep -q "<path>/$ROM_ROOT/" /etc/emulationstation/es_systems.cfg; then
    rollback_update
    rm -f "$UPDATE_ZIP"
    rm -rf "$UPDATE_STAGE"
    printf "\nROM path configuration changed unexpectedly; previous files restored.\n" | tee -a "$LOG_FILE"
    exit 1
  fi

  rm -f "$UPDATE_ZIP"
  rm -rf "$UPDATE_STAGE"
  touch "/home/ark/.config/.update10032026"
  echo "10032026" > /home/ark/.config/.VERSION
  sudo sed -i "/title\=/c\title\=dArkOSRE (10032026)" /usr/share/plymouth/themes/text.plymouth
  printf "\nInstalled RK3326 update. ROM library remains on /$ROM_ROOT; rollback files are in $BACKUP_BASE.\n" | tee -a "$LOG_FILE"
  sudo systemctl reboot
  exit 187
fi

# Follow-up R36S-only adaptation release. Keep the already-published base OTA
# unchanged and version the patch separately. It only replaces scoped scripts
# and applies the two known Atari command fixes without touching ROM paths.
PATCH_VERSION="10032026-r1"
if [ ! -f "/home/ark/.config/.update$PATCH_VERSION" ]; then
  BASE_VERSION="$(cat /home/ark/.config/.VERSION 2>/dev/null)"
  if [[ "$(tr -d '\0' < /proc/device-tree/compatible 2>/dev/null)" != *"rk3326"* ]] || [ "$BASE_VERSION" != "10032026" ]; then
    printf "\nThis update requires dArkOSRE-R36 RK3326 OTA 10032026; no files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  fi

  printf "\nInstall R36 Singe/ZLua and settings-backup fixes while preserving /roms and /roms2...\n" | tee -a "$LOG_FILE"
  UPDATE_ZIP="/dev/shm/darkosupdate$PATCH_VERSION.zip"
  UPDATE_STAGE="/tmp/darkos-update$PATCH_VERSION.$$"
  UPDATE_URL="$LOCATION/$PATCH_VERSION/darkosupdate$PATCH_VERSION.zip"
  UPDATE_SHA256="12987d5fcc7bd889b922f3e0083b2e454c002b0d7dce6a6c26f192b7ea9b429b"

  if mountpoint -q /roms2; then
    ROM_ROOT="roms2"
    BACKUP_BASE="/roms2/backup/darkosre-update/$PATCH_VERSION"
  else
    ROM_ROOT="roms"
    BACKUP_BASE="/roms/backup/darkosre-update/$PATCH_VERSION"
  fi

  PATHS_BEFORE="$(grep -o '<path>[^<]*</path>' /etc/emulationstation/es_systems.cfg 2>/dev/null)"
  SWITCH_GUARD_BEFORE="$(sed '/\/usr\/local\/bin\/singe\.sh/d' "/usr/local/bin/Switch to SD2 for Roms.sh" | sha256sum; \
    sed '/\/usr\/local\/bin\/singe\.sh/d' "/usr/local/bin/Switch to Main SD for Roms.sh" | sha256sum)"
  SINGE_SWITCH_LINES="$(grep -c '/usr/local/bin/singe\.sh' "/usr/local/bin/Switch to SD2 for Roms.sh"; \
    grep -c '/usr/local/bin/singe\.sh' "/usr/local/bin/Switch to Main SD for Roms.sh")"
  if ! awk 'NF && ($1 !~ /^[01]$/) {bad=1} END {exit bad || NR != 2}' <<< "$SINGE_SWITCH_LINES"; then
    printf "\nUnexpected Singe path rewrite in the ROM-card switch scripts; update stopped.\n" | tee -a "$LOG_FILE"
    exit 1
  fi
  if [ -z "$PATHS_BEFORE" ] || [ "$(printf '%s\n' "$SWITCH_GUARD_BEFORE" | sed '/^$/d' | wc -l)" -ne 2 ] || \
     ! grep -Fq "<path>/$ROM_ROOT/" /etc/emulationstation/es_systems.cfg; then
    printf "\nROM-card selection could not be verified; update stopped without installing files.\n" | tee -a "$LOG_FILE"
    exit 1
  fi

  sudo mkdir -p "$BACKUP_BASE" || exit 1
  mkdir -p "$UPDATE_STAGE" || exit 1
  if ! sudo touch "$BACKUP_BASE/.write-test"; then
    printf "\nCould not create a rollback backup on the active ROM card.\n" | tee -a "$LOG_FILE"
    rm -rf "$UPDATE_STAGE"
    exit 1
  fi
  sudo rm -f "$BACKUP_BASE/.write-test"

  AVAILABLE_TMP_KB="$(df -Pk /tmp | awk 'NR==2 {print $4}')"
  if [ "${AVAILABLE_TMP_KB:-0}" -lt 120000 ]; then
    printf "\nNot enough temporary storage; update stopped before installation.\n" | tee -a "$LOG_FILE"
    rm -rf "$UPDATE_STAGE"
    exit 1
  fi

  wget -t 3 -T 120 --no-check-certificate "$UPDATE_URL" -O "$UPDATE_ZIP" -a "$LOG_FILE" || {
    rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
    printf "\nCould not download the update package.\n" | tee -a "$LOG_FILE"
    exit 1
  }
  echo "$UPDATE_SHA256  $UPDATE_ZIP" | sha256sum -c - || {
    rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
    printf "\nUpdate archive checksum did not match; no files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  }
  unzip -t "$UPDATE_ZIP" >/dev/null || {
    rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
    printf "\nUpdate archive validation failed; no files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  }
  if unzip -Z1 "$UPDATE_ZIP" | grep -Eq '^(etc/emulationstation/es_systems.cfg|usr/local/bin/Switch to (SD2|Main SD) for Roms.sh|opt/system/Advanced/Switch to (SD2|Main SD) for Roms.sh|roms/|roms2/)'; then
    rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
    printf "\nUpdate archive contains a ROM-root or SD-switch file; installation refused.\n" | tee -a "$LOG_FILE"
    exit 1
  fi
  unzip -q -o "$UPDATE_ZIP" -d "$UPDATE_STAGE" || {
    rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
    printf "\nCould not stage update archive; no system files were installed.\n" | tee -a "$LOG_FILE"
    exit 1
  }

  UPDATE_PATHS=(
    "etc/emulationstation/es_systems.cfg"
    "home/ark/.emulationstation/themes"
    "opt/system/Advanced/Backup dArkOS Settings.sh"
    "opt/system/Advanced/Restore dArkOS Settings.sh"
    "usr/local/bin/Switch to SD2 for Roms.sh"
    "usr/local/bin/Switch to Main SD for Roms.sh"
    "usr/local/bin/auto_suspend.py"
    "usr/local/bin/daphne.sh"
    "usr/local/bin/singe.sh"
  )
  BACKUP_ARCHIVE="$BACKUP_BASE/rollback.tar"
  if [ ! -f "$BACKUP_BASE/backup-ready" ]; then
    sudo rm -rf "$BACKUP_BASE"
    sudo mkdir -p "$BACKUP_BASE" || exit 1
    printf '%s\n' "${UPDATE_PATHS[@]}" | sudo tee "$BACKUP_BASE/managed-paths.txt" >/dev/null
    sudo truncate -s 0 "$BACKUP_BASE/existed-paths.txt"
    EXISTED_PATHS=()
    for item in "${UPDATE_PATHS[@]}"; do
      if [ -e "/$item" ] || [ -L "/$item" ]; then
        EXISTED_PATHS+=("$item")
        printf '%s\n' "$item" | sudo tee -a "$BACKUP_BASE/existed-paths.txt" >/dev/null
      fi
    done
    if ((${#EXISTED_PATHS[@]})); then
      sudo tar --numeric-owner -cpf "$BACKUP_ARCHIVE.tmp" -C / -- "${EXISTED_PATHS[@]}" || {
        rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
        printf "\nRollback archive creation failed; update stopped before installation.\n" | tee -a "$LOG_FILE"
        exit 1
      }
    else
      sudo tar -cpf "$BACKUP_ARCHIVE.tmp" --files-from=/dev/null || exit 1
    fi
    if ! sudo tar -tf "$BACKUP_ARCHIVE.tmp" >/dev/null; then
      rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
      printf "\nRollback archive validation failed; update stopped before installation.\n" | tee -a "$LOG_FILE"
      exit 1
    fi
    sudo mv "$BACKUP_ARCHIVE.tmp" "$BACKUP_ARCHIVE" || exit 1
    sudo sha256sum "$BACKUP_ARCHIVE" | sudo tee "$BACKUP_BASE/rollback.sha256" >/dev/null
    sudo touch "$BACKUP_BASE/backup-ready"
  else
    if ! cmp -s <(printf '%s\n' "${UPDATE_PATHS[@]}") "$BACKUP_BASE/managed-paths.txt"; then
      printf "\nExisting rollback snapshot does not match this update; update stopped.\n" | tee -a "$LOG_FILE"
      rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
      exit 1
    fi
    EXPECTED_BACKUP_SHA256="$(awk 'NR == 1 {print $1}' "$BACKUP_BASE/rollback.sha256" 2>/dev/null)"
    ACTUAL_BACKUP_SHA256="$(sha256sum "$BACKUP_ARCHIVE" 2>/dev/null | awk '{print $1}')"
    if [ -z "$EXPECTED_BACKUP_SHA256" ] || [ "$EXPECTED_BACKUP_SHA256" != "$ACTUAL_BACKUP_SHA256" ] || ! sudo tar -tf "$BACKUP_ARCHIVE" >/dev/null; then
      printf "\nRollback archive is missing or damaged; update stopped.\n" | tee -a "$LOG_FILE"
      rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
      exit 1
    fi
  fi

  rollback_patch() {
    printf "\nInstallation failed; restoring the previous files from $BACKUP_BASE\n" | tee -a "$LOG_FILE"
    local failed=0
    for item in "${UPDATE_PATHS[@]}"; do sudo rm -rf "/$item" || failed=1; done
    sudo tar --numeric-owner -xpf "$BACKUP_ARCHIVE" -C / || failed=1
    return "$failed"
  }

  for item in "${UPDATE_PATHS[@]}"; do
    if [ -e "$UPDATE_STAGE/$item" ] || [ -L "$UPDATE_STAGE/$item" ]; then
      sudo mkdir -p "/$(dirname "$item")"
      sudo rm -rf "/$item"
      sudo cp -a "$UPDATE_STAGE/$item" "/$(dirname "$item")/" || { rollback_patch; exit 1; }
      if [ ! -L "/$item" ]; then sudo chown root:root "/$item" || { rollback_patch; exit 1; }; fi
    fi
  done

  # singe.sh now resolves /roms versus /roms2 from the selected shortcut.
  # Remove only the legacy sed lines that would corrupt that dual-root logic.
  sudo sed -i '\|/usr/local/bin/singe\.sh|d' "/usr/local/bin/Switch to SD2 for Roms.sh" || { rollback_patch; exit 1; }
  sudo sed -i '\|/usr/local/bin/singe\.sh|d' "/usr/local/bin/Switch to Main SD for Roms.sh" || { rollback_patch; exit 1; }

  # Preserve user themes. Make the vanilla dual-card link only when the path
  # is absent or is already a symlink; never replace a real theme directory.
  if mountpoint -q /roms2 && [ -d /roms2/themes ] && { [ ! -e /home/ark/.emulationstation/themes ] || [ -L /home/ark/.emulationstation/themes ]; }; then
    sudo ln -sfn /roms2/themes /home/ark/.emulationstation/themes || { rollback_patch; exit 1; }
  fi

  # Port vanilla's Atari 800/XEGS default-core fix without replacing the local
  # XML or changing any of its ROM path entries.
sudo python3 - <<'PY'
import os, re, stat, tempfile
path = "/etc/emulationstation/es_systems.cfg"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
original = content
for system, config in (("atari800", "retroarch_A800.cfg"), ("atarixegs", "retroarch_XEGS.cfg")):
    pattern = re.compile(r"<system>(?:(?!</system>).)*?<name>" + re.escape(system) + r"</name>(?:(?!</system>).)*?</system>", re.S)
    matches = list(pattern.finditer(content))
    if len(matches) != 1:
        raise SystemExit(f"expected one {system} system section, found {len(matches)}")
    block = matches[0].group(0)
    old = "--config /home/ark/.config/retroarch/config/Atari800/" + config + " "
    if old in block:
        block = block.replace(old, "", 1)
    elif "retroarch --config" in block and config in block:
        raise SystemExit(f"unexpected Atari config command for {system}")
    content = content[:matches[0].start()] + block + content[matches[0].end():]
if content != original:
    mode = stat.S_IMODE(os.stat(path).st_mode)
    fd, tmp = tempfile.mkstemp(prefix=".es_systems.cfg.", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
PY
  PATCH_STATUS=$?
  PATHS_AFTER="$(grep -o '<path>[^<]*</path>' /etc/emulationstation/es_systems.cfg 2>/dev/null)"
  SWITCH_GUARD_AFTER="$(sed '/\/usr\/local\/bin\/singe\.sh/d' "/usr/local/bin/Switch to SD2 for Roms.sh" | sha256sum; \
    sed '/\/usr\/local\/bin\/singe\.sh/d' "/usr/local/bin/Switch to Main SD for Roms.sh" | sha256sum)"
  if [ "$PATCH_STATUS" -ne 0 ] || [ "$PATHS_BEFORE" != "$PATHS_AFTER" ] || \
     [ "$SWITCH_GUARD_BEFORE" != "$SWITCH_GUARD_AFTER" ] || \
     ! grep -Fq "<path>/$ROM_ROOT/" /etc/emulationstation/es_systems.cfg; then
    rollback_patch
    rm -f "$UPDATE_ZIP"; rm -rf "$UPDATE_STAGE"
    printf "\nROM paths or SD switch scripts changed unexpectedly; previous files restored.\n" | tee -a "$LOG_FILE"
    exit 1
  fi

  rm -f "$UPDATE_ZIP"
  rm -rf "$UPDATE_STAGE"
  touch "/home/ark/.config/.update$PATCH_VERSION"
  echo "$PATCH_VERSION" > /home/ark/.config/.VERSION
  sudo sed -i "/title=/c\\title=dArkOSRE ($PATCH_VERSION)" /usr/share/plymouth/themes/text.plymouth
  printf "\nInstalled R36S fixes. ROM library remains on /$ROM_ROOT; rollback is saved under $BACKUP_BASE.\n" | tee -a "$LOG_FILE"
  sudo systemctl reboot
  exit 187
fi
