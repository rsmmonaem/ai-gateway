#!/usr/bin/env bash

echo "Waiting for Apple Developer Command Line Tools installation to finish..."
until xcode-select -p &>/dev/null; do
    sleep 3
done

echo "Apple Developer Command Line Tools detected at $(xcode-select -p)!"
echo "Proceeding with Homebrew and AI Gateway setup..."
./infrastructure/scripts/setup-mac-m4.sh
