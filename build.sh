#!/bin/bash

# We need: copr, git, fedpkg

set -e
set -o pipefail
set -u
#set -x

START_TIME=${SECONDS}
PACKAGES="${PACKAGES:-ior istio istio-cni istio-operator}"
COPR_REPO="${COPR_REPO:-jwendell/istio}"
TIME_WAIT=${TIME_WAIT:-1200}
BUILD_IDS=()

function error() {
  [ $# -gt 0 ] && echo "$@"
  exit 1
}

function generate_srpm() {
  # This command should only download the upstream tarball and not touch anything else
  ./update.sh
  # [[ -n "$(git status --porcelain)" ]] && error

  fedpkg --release el8 srpm
}

function invoke_copr_build() {
  local re='^[0-9]+$'
  local build_id

  build_id=$(copr build --nowait "${COPR_REPO}" ./*.src.rpm | grep 'Created builds:' | awk '{print $3}')
  if [[ ! ${build_id} =~ ${re} ]]; then
    error "Error invoking copr to build the package"
  fi

  BUILD_IDS+=("${build_id}")
}

function build_package() {
  local package="${1}"

  echo
  echo "Building ${package}"
  pushd "${package}" >/dev/null

  generate_srpm
  invoke_copr_build

  popd >/dev/null
}

function build_packages() {
  echo "Starting building of packages: ${PACKAGES}"

  for package in ${PACKAGES}; do
    build_package "${package}"
  done
}

function print_build_urls() {
  for build_id in "$@"; do
    echo "https://copr.fedorainfracloud.org/coprs/build/${build_id}/"
  done
}

function wait_for_build_to_finish() {
  local builds=("${BUILD_IDS[@]}")
  local succedeed_builds=()
  local failed_builds=()
  local keep_trying=true
  local computed_builds
  local computed_time
  local start_time=${SECONDS}
  local result

  SECONDS=0
  echo
  echo "Waiting for COPR builds to finish (max wait time: ${TIME_WAIT}s"

  while [ "${keep_trying}" = "true" ]; do
    sleep 10

    local next_builds=()
    for build_id in "${builds[@]}"; do
      result=$(copr status "${build_id}")
      case ${result} in
        succeeded)
          echo "Build $(print_build_urls "${build_id}") succeeded"
          succedeed_builds+=("${build_id}")
          ;;

        pending | importing | running)
          next_builds+=("${build_id}")
          ;;

        *)
          echo "Build $(print_build_urls "${build_id}") failed"
          failed_builds+=("${build_id}")
          ;;
      esac
    done
 
    computed_builds=$(( ${#succedeed_builds[@]} + ${#failed_builds[@]} ))
    computed_time=$(( SECONDS - start_time ))
    if [[ ${computed_builds} -eq ${#BUILD_IDS[@]} ]] || [[ ${computed_time} -ge ${TIME_WAIT} ]]; then
      keep_trying=false
    else
      builds=("${next_builds[@]}")
    fi

  done

  echo
  if [[ ${#succedeed_builds[@]} -eq ${#BUILD_IDS[@]} ]]; then
    echo "All builds succeeded!"
  else
    echo "One or more builds failed. Check them out:"
    print_build_urls "${failed_builds[@]}"
    print_build_urls "${next_builds[@]}"
    error
  fi
}

function main() {
  build_packages
  wait_for_build_to_finish

  echo
  echo "Elapsed time: $(( SECONDS - START_TIME ))s"
  echo
}

main
