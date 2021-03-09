#!/bin/bash
#D=$(date -j -v-1d "+%Y%m%d")
D=20201215  # known to work
URL="https://valelab4.ucsf.edu/~MM/nightlyBuilds/2.0.0-gamma/Mac/Micro-Manager-2.0.0-gamma1-$D.dmg"
curl -k $URL -o mm.dmg
hdiutil attach -nobrowse mm.dmg
echo copying...
cp -r /Volumes/Micro-Manager/Micro-Manager-* micromanager_gui
ls micromanager_gui
rm mm.dmg
hdiutil detach /Volumes/Micro-Manager
# fix gatekeeper ... requires password
sudo xattr -r -d com.apple.quarantine micromanager_gui/Micro-Manager-*
# fix path randomization
mv micromanager_gui/Micro-Manager-*/ImageJ.app ~
mv ~/ImageJ.app micromanager_gui/Micro-Manager-*
