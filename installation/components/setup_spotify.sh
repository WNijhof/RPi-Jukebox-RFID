#!/usr/bin/env bash
# Eigen uitbreiding muziekbox: Spotify Connect (Spotify Soloist) + koppeling met Spotify-account
#
# Usage:
#   ./setup_spotify.sh              install Soloist (if needed) and connect the Spotify account
#   ./setup_spotify.sh soloist      only install/update the Soloist speaker service
#   ./setup_spotify.sh update       download a newer Soloist build if available (run daily by soloist-update.timer)
#   ./setup_spotify.sh auth         only (re-)connect the Spotify account
#
# Optional: DEVICE_NAME="Muziekbox" ./setup_spotify.sh
#
# Soloist is Spotify's official headless Spotify Connect client. It needs an API key from
# https://developer.spotify.com (Spotify Soloist API Key page), stored in ${KEY_FILE}.
# The builds need glibc >= 2.38. On older systems (Raspberry Pi OS Bookworm) a private copy
# of the Debian Trixie glibc is used for Soloist only; the rest of the system is untouched.
# Builds expire after 90 days, hence the daily update timer.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEVICE_NAME="${DEVICE_NAME:-Muziekbox}"
SOLOIST_DIR="${HOME}/.local/lib/soloist"
KEY_FILE="${HOME}/.config/soloist/soloist.env"
USER_SERVICE_DIR="${HOME}/.config/systemd/user"
SOLOIST_DOWNLOAD_URL="https://soloist-builds.spotifycdn.com/soloist_release_%ARCH%.tar.gz"
DEBIAN_GLIBC_URL="https://deb.debian.org/debian"
DEBIAN_GLIBC_SUITE="trixie"
GLIBC_REQUIRED="2.38"

soloist_arch() {
  case "$(uname -m)" in
    armv7l) echo "arm32" ;;
    aarch64) echo "arm64" ;;
    x86_64) echo "x86_64" ;;
    *) echo "ERROR: Soloist is not available for $(uname -m)" >&2; return 1 ;;
  esac
}

debian_arch() {
  case "$1" in
    arm32) echo "armhf" ;;
    arm64) echo "arm64" ;;
    x86_64) echo "amd64" ;;
  esac
}

needs_private_glibc() {
  local system_glibc
  system_glibc=$(ldd --version | head -n 1 | grep -oE '[0-9]+\.[0-9]+$')
  [[ "$(printf '%s\n%s\n' "${GLIBC_REQUIRED}" "${system_glibc}" | sort -V | head -n 1)" != "${GLIBC_REQUIRED}" ]]
}

install_private_glibc() {
  local arch deb_arch tmp_dir
  arch=$(soloist_arch)
  deb_arch=$(debian_arch "${arch}")
  echo "==> Glibc ${GLIBC_REQUIRED}+ uit Debian ${DEBIAN_GLIBC_SUITE} ophalen (alleen voor Soloist)"
  tmp_dir=$(mktemp -d)
  curl -sS --fail "${DEBIAN_GLIBC_URL}/dists/${DEBIAN_GLIBC_SUITE}/main/binary-${deb_arch}/Packages.xz" \
    | xz -d > "${tmp_dir}/Packages"
  for pkg in libc6 libatomic1; do
    local deb_path
    deb_path=$(awk -v p="${pkg}" '/^Package: /{ok=($2==p)} ok && /^Filename: /{print $2; exit}' "${tmp_dir}/Packages")
    [[ -n "${deb_path}" ]] || { echo "ERROR: ${pkg} not found in Debian ${DEBIAN_GLIBC_SUITE}"; exit 1; }
    curl -sS --fail -o "${tmp_dir}/${pkg}.deb" "${DEBIAN_GLIBC_URL}/${deb_path}"
    dpkg-deb -x "${tmp_dir}/${pkg}.deb" "${tmp_dir}/root"
  done
  rm -rf "${SOLOIST_DIR}/glibc"
  mv "${tmp_dir}/root" "${SOLOIST_DIR}/glibc"
  rm -rf "${tmp_dir}"
}

# Point the binary at the private glibc (interpreter + rpath). The PipeWire/PulseAudio client
# libraries Soloist loads at runtime still come from the system library directories.
link_private_glibc() {
  local binary="$1"
  needs_private_glibc || return 0
  [[ -d "${SOLOIST_DIR}/glibc" ]] || install_private_glibc
  command -v patchelf > /dev/null || sudo apt-get install -y patchelf
  local lib_dir loader
  lib_dir=$(dirname "$(find "${SOLOIST_DIR}/glibc" -name 'libc.so.6' | head -n 1)")
  loader="${lib_dir}/$(basename "$(find "${SOLOIST_DIR}/glibc" -name 'ld-linux*.so.*' | head -n 1)")"
  chmod u+w "${binary}"
  patchelf --set-interpreter "${loader}" --set-rpath "${lib_dir}" "${binary}"
}

# Downloads the Soloist build; returns 1 if the installed build is already the latest
download_soloist() {
  local arch url tmp_dir
  arch=$(soloist_arch)
  url="${SOLOIST_DOWNLOAD_URL/\%ARCH\%/${arch}}"
  mkdir -p "${SOLOIST_DIR}"
  tmp_dir=$(mktemp -d)
  # Only download if newer than the archive we have
  if [[ -f "${SOLOIST_DIR}/soloist.tar.gz" ]]; then
    cp -p "${SOLOIST_DIR}/soloist.tar.gz" "${tmp_dir}/soloist.tar.gz"
    curl -sS --fail --location -z "${tmp_dir}/soloist.tar.gz" -o "${tmp_dir}/soloist.tar.gz" -R "${url}"
    if cmp -s "${tmp_dir}/soloist.tar.gz" "${SOLOIST_DIR}/soloist.tar.gz"; then
      rm -rf "${tmp_dir}"
      return 1
    fi
  else
    curl -sS --fail --location -o "${tmp_dir}/soloist.tar.gz" -R "${url}"
  fi
  tar -xzf "${tmp_dir}/soloist.tar.gz" -C "${tmp_dir}" soloist
  test -x "${tmp_dir}/soloist"
  link_private_glibc "${tmp_dir}/soloist"
  "${tmp_dir}/soloist" --version > /dev/null
  mv -f "${tmp_dir}/soloist" "${SOLOIST_DIR}/soloist"
  mv -f "${tmp_dir}/soloist.tar.gz" "${SOLOIST_DIR}/soloist.tar.gz"
  rm -rf "${tmp_dir}"
}

ask_api_key() {
  mkdir -p "$(dirname "${KEY_FILE}")"
  if [[ -s "${KEY_FILE}" ]]; then
    echo "==> API-sleutel gevonden in ${KEY_FILE}"
    return
  fi
  echo
  echo "Soloist heeft een API-sleutel nodig. Maak die aan op developer.spotify.com"
  echo "(Spotify Soloist API Key), met een account dat Premium heeft."
  read -r -s -p "Plak de API-sleutel (je ziet niets tijdens het plakken): " api_key
  echo
  [[ -n "${api_key}" ]] || { echo "ERROR: geen API-sleutel opgegeven"; exit 1; }
  (umask 077 && printf 'SOLOIST_API_KEY=%s\n' "${api_key}" > "${KEY_FILE}")
}

install_service() {
  local name="$1"
  sed -e "s|%%DEVICE_NAME%%|${DEVICE_NAME}|g" -e "s|%%SOLOIST_DIR%%|${SOLOIST_DIR}|g" \
    -e "s|%%PROJECT_ROOT%%|${PROJECT_ROOT}|g" \
    "${PROJECT_ROOT}/resources/default-services/${name}" > "${USER_SERVICE_DIR}/${name}"
}

install_soloist() {
  echo "==> Spotify Soloist installeren in ${SOLOIST_DIR}"
  download_soloist || echo "    Nieuwste versie staat er al"
  "${SOLOIST_DIR}/soloist" --version

  ask_api_key

  # The previous speaker (librespot) would show up as a second device with the same name
  if systemctl --user list-unit-files librespot.service > /dev/null 2>&1; then
    echo "==> Oude librespot-dienst uitzetten"
    systemctl --user disable --now librespot.service || true
    rm -f "${USER_SERVICE_DIR}/librespot.service"
  fi

  echo "==> User services soloist.service en soloist-update.timer aanmaken (naam: ${DEVICE_NAME})"
  mkdir -p "${USER_SERVICE_DIR}"
  install_service soloist.service
  install_service soloist-update.service
  install_service soloist-update.timer

  # Keep user services running without anybody logged in
  sudo loginctl enable-linger "$(whoami)"

  systemctl --user daemon-reload
  systemctl --user enable soloist.service soloist-update.timer
  systemctl --user restart soloist.service
  systemctl --user start soloist-update.timer
  sleep 3
  systemctl --user --no-pager status soloist.service | head -n 5 || true
  echo
  echo "Open nu op je telefoon de Spotify-app (ingelogd met het account van de box),"
  echo "tik op het luidspreker-icoon en kies '${DEVICE_NAME}'. Dit is eenmalig nodig:"
  echo "Soloist onthoudt de koppeling daarna in ~/.local/share/soloist."
  echo
}

update_soloist() {
  if download_soloist; then
    echo "==> Nieuwe Soloist-build geinstalleerd: $("${SOLOIST_DIR}/soloist" --version)"
    systemctl --user restart soloist.service
  else
    echo "==> Soloist is up-to-date"
  fi
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
  soloist) install_soloist ;;
  update) update_soloist ;;
  auth) connect_account ;;
  all) install_soloist; read -r -p "Druk op Enter als de box in de Spotify-app als luidspreker gekozen is..."; connect_account ;;
  *) echo "Usage: $0 [soloist|update|auth]"; exit 1 ;;
esac
