#!/usr/bin/env bash
# Eigen uitbreiding muziekbox: update the box to the latest GitHub release of our fork
#
# Usage:
#   ./update_jukebox.sh            update if there is a new release (run by jukebox-update.timer)
#   ./update_jukebox.sh install    install and start the timer (once per box)
#
# Only real releases count: GitHub leaves out pre-releases like 'eigen-webapp'.
# The update waits while music is playing and until the Web App bundle of the release
# commit is built (eigen_webapp_build.yml). If the Jukebox does not come back after the
# update, the old version is restored and that release is not tried again.
#
# The merge replaces this file while it runs. Everything is in functions and the last
# line exits, so bash never reads the changed file.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
GITHUB_REPO="${GITHUB_REPO:-WNijhof/RPi-Jukebox-RFID}"
GITHUB_API_URL="${GITHUB_API_URL:-https://api.github.com}"
GITHUB_URL="${GITHUB_URL:-https://github.com}"
WEBAPP_RELEASE_TAG="eigen-webapp"
WEBAPP_DIR="${PROJECT_ROOT}/src/webapp"
USER_SERVICE_DIR="${HOME}/.config/systemd/user"
STATE_DIR="${HOME}/.local/state/jukebox-update"
FAILED_FILE="${STATE_DIR}/failed-commit"
JUKEBOX_START_TIMEOUT="${JUKEBOX_START_TIMEOUT:-180}"

latest_release_tag() {
  curl -sS --fail --location --max-time 30 "${GITHUB_API_URL}/repos/${GITHUB_REPO}/releases/latest" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])' 2> /dev/null
}

player_status() {
  (cd "${PROJECT_ROOT}/src/jukebox" && ../../.venv/bin/python run_rpc_tool.py -c player.ctrl.playerstatus 2>&1) || true
}

is_playing() {
  player_status | grep -q "'state': 'play'"
}

wait_for_jukebox() {
  local waited=0
  while (( waited < JUKEBOX_START_TIMEOUT )); do
    if player_status | grep -q "Response ="; then
      return 0
    fi
    sleep 5
    waited=$((waited + 5))
  done
  return 1
}

# Returns 1 if there is no bundle (yet) for this commit
download_webapp() {
  local commit="$1" work_dir="$2"
  local url="${GITHUB_URL}/${GITHUB_REPO}/releases/download/${WEBAPP_RELEASE_TAG}/webapp-build-${commit:0:10}.tar.gz"
  curl -sS --fail --location --max-time 300 -o "${work_dir}/webapp.tar.gz" "${url}" || return 1
  tar -xzf "${work_dir}/webapp.tar.gz" -C "${work_dir}" || return 1
  [[ -f "${work_dir}/build/index.html" ]] || return 1
  chmod -R a+rX "${work_dir}/build"
}

replace_webapp() {
  local work_dir="$1"
  rm -rf "${WEBAPP_DIR}/build-backup"
  if [[ -d "${WEBAPP_DIR}/build" ]]; then
    mv "${WEBAPP_DIR}/build" "${WEBAPP_DIR}/build-backup"
  fi
  mv "${work_dir}/build" "${WEBAPP_DIR}/build"
}

restore_webapp() {
  if [[ -d "${WEBAPP_DIR}/build-backup" ]]; then
    rm -rf "${WEBAPP_DIR}/build"
    mv "${WEBAPP_DIR}/build-backup" "${WEBAPP_DIR}/build"
  fi
}

install_python_requirements() {
  "${PROJECT_ROOT}/.venv/bin/python" -m pip install --upgrade -r "${PROJECT_ROOT}/requirements.txt" || return 1
  "${PROJECT_ROOT}/.venv/bin/python" -m pip uninstall -y -r "${PROJECT_ROOT}/requirements-excluded.txt"
}

install_system_packages() {
  sudo apt-get -y update || return 1
  sed 's/#.*//g' "${PROJECT_ROOT}/packages-core.txt" | xargs sudo apt-get -y install --no-install-recommends
}

changed_between() {
  local old="$1" new="$2"
  shift 2
  ! git diff --quiet "${old}" "${new}" -- "$@"
}

install_release() {
  local old="$1" new="$2" work_dir="$3"
  git merge --quiet --ff-only "${new}" || return 1
  if changed_between "${old}" "${new}" packages-core.txt; then
    install_system_packages || return 1
  fi
  if changed_between "${old}" "${new}" requirements.txt requirements-excluded.txt; then
    install_python_requirements || return 1
  fi
  replace_webapp "${work_dir}" || return 1
  systemctl --user start jukebox-daemon.service || return 1
  wait_for_jukebox
}

roll_back() {
  local old="$1" new="$2"
  echo "==> Update mislukt, terug naar ${old:0:10}"
  systemctl --user stop jukebox-daemon.service || true
  git reset --quiet --hard "${old}"
  restore_webapp
  if changed_between "${old}" "${new}" requirements.txt requirements-excluded.txt; then
    install_python_requirements || true
  fi
  systemctl --user start jukebox-daemon.service
  mkdir -p "${STATE_DIR}"
  echo "${new}" > "${FAILED_FILE}"
  if wait_for_jukebox; then
    echo "==> Oude versie draait weer"
  else
    echo "ERROR: ook de oude versie start niet"
  fi
}

update_jukebox() {
  local tag old new work_dir

  cd "${PROJECT_ROOT}"

  if [[ "$(findmnt -n -o FSTYPE /)" == "overlay" ]]; then
    echo "==> Read-only overlay staat aan: een update zou na herstart weg zijn, overslaan"
    return 0
  fi

  if ! tag=$(latest_release_tag) || [[ -z "${tag}" ]]; then
    echo "==> Geen release gevonden (of geen internet)"
    return 0
  fi

  git fetch --quiet --no-tags origin "+refs/tags/${tag}:refs/tags/${tag}"
  new=$(git rev-parse "refs/tags/${tag}^{commit}")
  old=$(git rev-parse HEAD)

  if [[ "${new}" == "${old}" ]]; then
    echo "==> Al op de nieuwste release (${tag})"
    return 0
  fi
  if ! git merge-base --is-ancestor HEAD "${new}"; then
    echo "==> Release ${tag} bouwt niet voort op deze versie, overslaan"
    return 0
  fi
  if [[ "$(cat "${FAILED_FILE}" 2> /dev/null)" == "${new}" ]]; then
    echo "==> Release ${tag} is eerder mislukt, overslaan"
    return 0
  fi
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "ERROR: lokale wijzigingen in ${PROJECT_ROOT}, release ${tag} overgeslagen"
    return 1
  fi
  if is_playing; then
    echo "==> Er speelt muziek, release ${tag} wacht tot de volgende controle"
    return 0
  fi

  mkdir -p "${STATE_DIR}"
  work_dir=$(mktemp -d "${STATE_DIR}/work.XXXXXX")
  # shellcheck disable=SC2064
  trap "rm -rf '${work_dir}'" EXIT
  if ! download_webapp "${new}" "${work_dir}"; then
    echo "==> Webpagina van ${tag} is nog niet gebouwd, wacht tot de volgende controle"
    return 0
  fi

  echo "==> Bijwerken naar ${tag} (${new:0:10})"
  systemctl --user stop jukebox-daemon.service
  if install_release "${old}" "${new}" "${work_dir}"; then
    rm -f "${FAILED_FILE}"
    echo "==> Klaar: release ${tag} draait"
    if changed_between "${old}" "${new}" resources/default-services installation; then
      echo "==> Let op: installatiebestanden gewijzigd, dit gaat niet automatisch"
    fi
  else
    roll_back "${old}" "${new}"
    return 1
  fi
}

install_service() {
  local name="$1"
  sed -e "s|%%PROJECT_ROOT%%|${PROJECT_ROOT}|g" \
    "${PROJECT_ROOT}/resources/default-services/${name}" > "${USER_SERVICE_DIR}/${name}"
}

install_timer() {
  echo "==> User services jukebox-update.service en jukebox-update.timer aanmaken"
  mkdir -p "${USER_SERVICE_DIR}"
  install_service jukebox-update.service
  install_service jukebox-update.timer

  # Keep user services running without anybody logged in
  sudo loginctl enable-linger "$(whoami)"

  systemctl --user daemon-reload
  systemctl --user enable --now jukebox-update.timer
  systemctl --user --no-pager list-timers jukebox-update.timer
}

main() {
  case "${1:-update}" in
    update) update_jukebox ;;
    install) install_timer ;;
    *) echo "Usage: $0 [update|install]"; exit 1 ;;
  esac
}

main "$@"; exit
