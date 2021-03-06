#!/bin/bash
mkdir mm
#D=$(date -j -v-1d "+%Y%m%d")
D=20201215  # known to work
URL="https://valelab4.ucsf.edu/~MM/nightlyBuilds/2.0.0-gamma/Mac/Micro-Manager-2.0.0-gamma1-$D.dmg"
curl -k $URL -o mm/mm.dmg
hdiutil attach mm/mm.dmg
cp -r /Volumes/Micro-Manager/Micro-Manager-* mm
rm mm/mm.dmg
hdiutil detach /Volumes/Micro-Manager
sudo xattr -r -d com.apple.quarantine mm
mv mm/Micro-Manager-2.0.0-gamma1-*/ImageJ.app ~
mv ~/ImageJ.app mm/Micro-Manager-2.0.0-gamma1-*
