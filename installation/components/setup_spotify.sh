#!/usr/bin/env bash
# Eigen uitbreiding muziekbox: Spotify Connect (librespot) + koppeling met Spotify-account
#
# Usage:
#   ./setup_spotify.sh              install librespot (if needed) and connect the Spotify account
#   ./setup_spotify.sh librespot    only install/update the librespot speaker service
#   ./setup_spotify.sh auth         only (re-)connect the Spotify account
#
# Optional: DEVICE_NAME="Muziekbox" BITRATE=160 ./setup_spotify.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEVICE_NAME="${DEVICE_NAME:-Muziekbox}"
BITRATE="${BITRATE:-160}"
SERVICE_FILE="${HOME}/.config/systemd/user/librespot.service"

install_librespot() {
  if ! command -v librespot > /dev/null; then
    echo "==> librespot installeren (via raspotify)"
    curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
  else
    echo "==> librespot is al geinstalleerd: $(command -v librespot)"
  fi

  # raspotify installs a system service that plays via ALSA directly.
  # We run librespot as user service instead, so it plays via the PulseAudio of the Jukebox
  # (and the Jukebox volume control / max volume also apply to Spotify).
  if systemctl list-unit-files raspotify.service > /dev/null 2>&1; then
    sudo systemctl disable --now raspotify.service || true
  fi

  echo "==> User service librespot.service aanmaken (naam: ${DEVICE_NAME})"
  mkdir -p "$(dirname "${SERVICE_FILE}")" "${HOME}/.cache/librespot"
  sed -e "s|%%DEVICE_NAME%%|${DEVICE_NAME}|g" -e "s|%%BITRATE%%|${BITRATE}|g" \
    "${PROJECT_ROOT}/resources/default-services/librespot.service" > "${SERVICE_FILE}"

  # Keep user services running without anybody logged in
  sudo loginctl enable-linger "$(whoami)"

  systemctl --user daemon-reload
  systemctl --user enable --now librespot.service
  sleep 2
  systemctl --user --no-pager status librespot.service | head -n 5 || true
  echo
  echo "Open nu op je telefoon de Spotify-app (ingelogd met het account van de box),"
  echo "tik op het luidspreker-icoon en kies '${DEVICE_NAME}'. Dit is eenmalig nodig:"
  echo "librespot onthoudt de inlog daarna in ~/.cache/librespot."
  echo
}

connect_account() {
  echo "==> Spotify-account koppelen"
  cd "${PROJECT_ROOT}"
  # shellcheck disable=SC1091
  source .venv/bin/activate || { echo "ERROR: Failed to activate virtual environment for python"; exit 1; }
  cd src/jukebox
  python run_spotify_auth.py
}

case "${1:-all}" in
  librespot) install_librespot ;;
  auth) connect_account ;;
  all) install_librespot; read -r -p "Druk op Enter als de box in de Spotify-app als luidspreker gekozen is..."; connect_account ;;
  *) echo "Usage: $0 [librespot|auth]"; exit 1 ;;
esac
