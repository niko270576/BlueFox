#!/bin/bash
# ════════════════════════════════════════════════════════════════════
#  Blue Fox ISO builder
#
#  Makes BlueFox.iso: a bootable system (USB / DVD) that starts straight
#  into Blue Fox in full screen, with Wi-Fi, sound, Firefox and Brave.
#
#  Runs automatically on GitHub (see .github/workflows/build-iso.yml).
#  To run it yourself you need Debian 12 (or a Debian 12 container) as root:
#      sudo bash build-iso.sh
#  The file bluefox.py must be in the same folder as this script.
# ════════════════════════════════════════════════════════════════════
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HERE/bluefox.py"
WORK="$HERE/_build"
OUT="$HERE/BlueFox.iso"

if [ "$(id -u)" != "0" ]; then echo "Please run as root: sudo bash build-iso.sh"; exit 1; fi
if [ ! -f "$APP" ]; then echo "bluefox.py was not found next to build-iso.sh"; exit 1; fi

echo "==> Installing the build tools"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends live-build debootstrap squashfs-tools xorriso isolinux \
    syslinux-common syslinux-utils grub-pc-bin grub-efi-amd64-bin grub-efi-amd64-signed shim-signed \
    mtools dosfstools ca-certificates curl gnupg python3 cpio

rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

echo "==> Configuring the system"
lb config noauto \
    --mode debian \
    --distribution bookworm \
    --architectures amd64 \
    --archive-areas "main contrib non-free non-free-firmware" \
    --binary-images iso-hybrid \
    --bootloaders "syslinux,grub-efi" \
    --debian-installer none \
    --apt-recommends false \
    --firmware-chroot false \
    --firmware-binary false \
    --memtest none \
    --iso-application "Blue Fox" \
    --iso-publisher "Blue Fox" \
    --iso-volume "BLUEFOX" \
    --bootappend-live "boot=live components quiet splash persistence username=user hostname=bluefox locales=en_US.UTF-8 keyboard-layouts=us,gr timezone=Europe/Athens"

# ── packages ─────────────────────────────────────────────────────────
mkdir -p config/package-lists
cat > config/package-lists/bluefox.list.chroot <<'EOF'
live-boot
live-config
live-config-systemd
systemd-sysv
sudo
locales
keyboard-configuration
console-setup
dbus-x11
polkitd
xserver-xorg
xserver-xorg-video-all
xserver-xorg-input-all
x11-xserver-utils
x11-xkb-utils
xinit
libgl1-mesa-dri
lightdm
lightdm-gtk-greeter
openbox
wmctrl
fonts-dejavu
fonts-liberation2
python3
python3-tk
network-manager
wpasupplicant
iw
ca-certificates
curl
pulseaudio
pulseaudio-utils
libasound2-plugins
alsa-utils
brightnessctl
upower
firefox-esr
firmware-linux-free
firmware-misc-nonfree
firmware-amd-graphics
firmware-iwlwifi
firmware-realtek
firmware-atheros
firmware-brcm80211
firmware-libertas
firmware-sof-signed
intel-microcode
amd64-microcode
EOF

# ── Blue Fox itself and how it starts ─────────────────────────────────
INC=config/includes.chroot
mkdir -p "$INC/opt/bluefox" "$INC/usr/local/bin" "$INC/usr/share/xsessions" "$INC/etc/lightdm/lightdm.conf.d"
cp "$APP" "$INC/opt/bluefox/bluefox.py"

cat > "$INC/usr/local/bin/bluefox-session" <<'EOF'
#!/bin/sh
# The Blue Fox desktop session: a tiny window manager + Blue Fox in full screen.
export BLUEFOX_SESSION=1
setxkbmap -layout us,gr -option grp:alt_shift_toggle 2>/dev/null || true
exec openbox-session
EOF
chmod 755 "$INC/usr/local/bin/bluefox-session"

cat > "$INC/usr/share/xsessions/bluefox.desktop" <<'EOF'
[Desktop Entry]
Name=Blue Fox
Comment=Blue Fox desktop
Exec=/usr/local/bin/bluefox-session
Type=Application
EOF

cat > "$INC/etc/lightdm/lightdm.conf.d/50-bluefox.conf" <<'EOF'
[Seat:*]
autologin-user=user
autologin-user-timeout=0
autologin-session=bluefox
user-session=bluefox
EOF

# ── final touches inside the system ──────────────────────────────────
mkdir -p config/hooks/normal
cat > config/hooks/normal/0500-bluefox.hook.chroot <<'EOF'
#!/bin/sh
set -e
# Window manager: keep the Blue Fox taskbar visible, Blue Fox itself without borders and full screen.
python3 - <<'PY'
import re
p = "/etc/xdg/openbox/rc.xml"
s = open(p).read()
s = re.sub(r"(<margins>.*?<bottom>)0(</bottom>)", r"\g<1>44\g<2>", s, count=1, flags=re.S)
rule = ('  <application title="BlueFoxDesktop">\n    <decor>no</decor>\n    <fullscreen>yes</fullscreen>\n'
        '    <focus>yes</focus>\n  </application>\n')
s = s.replace("</applications>", rule + "</applications>", 1)
open(p, "w").write(s)
PY
# Start Blue Fox with the session (and start it again if it ever closes).
cat >> /etc/xdg/openbox/autostart <<'AUTO'
xsetroot -solid "#04122e" &
(while true; do python3 /opt/bluefox/bluefox.py; sleep 1; done) &
AUTO
# Live user: allowed to manage Wi-Fi and to install programs from the Fox Store.
echo 'user ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/bluefox
chmod 440 /etc/sudoers.d/bluefox
echo bluefox > /etc/hostname
EOF

cat > config/hooks/normal/0600-brave.hook.chroot <<'EOF'
#!/bin/sh
# Brave browser (from Brave's own official package repository). The ISO still builds if this fails.
set +e
apt-get install -y --no-install-recommends gnupg curl ca-certificates
curl -fsSLo /usr/share/keyrings/brave-browser-archive-keyring.gpg \
    https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg && \
echo "deb [signed-by=/usr/share/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main" \
    > /etc/apt/sources.list.d/brave-browser-release.list && \
apt-get update && apt-get install -y --no-install-recommends brave-browser || echo "!! Brave could not be installed"
apt-get clean
exit 0
EOF

# Boot menu says "Blue Fox"
cat > config/hooks/normal/0900-branding.hook.binary <<'EOF'
#!/bin/sh
set +e
for f in boot/grub/grub.cfg boot/grub/*.cfg isolinux/*.cfg binary/boot/grub/*.cfg binary/isolinux/*.cfg; do
    [ -f "$f" ] && sed -i 's/Live system/Blue Fox/g; s/Debian GNU\/Linux/Blue Fox/g' "$f"
done
exit 0
EOF
chmod 755 config/hooks/normal/*

echo "==> Building the ISO (this takes a while)"
lb build 2>&1 | tee build.log
ISO="$(ls -1 "$WORK"/*.iso 2>/dev/null | head -n1 || true)"
if [ -z "$ISO" ]; then echo "!! The ISO was not created. See _build/build.log"; exit 1; fi
mv "$ISO" "$OUT"
echo "==> Done: $OUT ($(du -h "$OUT" | cut -f1))"
