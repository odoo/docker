#!/bin/bash
# #####
#
# Generate Odoo release.txt files.
#
# usage:
#   # all
#   bash generate_releases.sh
#
#   # from a specific day
#   bash generate_release.sh 2016-12-30
#
# author: Pedro Salgado <steenzout@ymail.com>
# version: 1.2
#
# #####

ARG_START="${1}"

fmt_date='%Y-%m-%d'
today=`date "+${fmt_date}"`
epoch=$(date -j -f "${fmt_date}" ${today} "+%s")
next=$((${epoch} + 86400))
tomorrow=$(date -j -f "%s" ${next} "+${fmt_date}")

for ODOO_VERSION in 8.0 9.0 10.0
do

  if [[ "${ARG_START}" != "" ]]; then
    day="${ARG_START}"
  elif [[ "${ODOO_VERSION}" == "8.0" ]]; then
    day=2014-11-28
  elif [[ "${ODOO_VERSION}" == "9.0" ]]; then
    day=2016-01-01
  elif [[ "${ODOO_VERSION}" == "10.0" ]]; then
    day=2016-10-05
  else
    echo "[ERROR] unknown version ${ODOO_VERSION}"
    exit 1
  fi
  echo "ARG_START=${ARG_START} day=${day}"

  echo "collecting SHA1 checksums for ${ODOO_VERSION} starting at ${day}..."
  rm -f "${ODOO_VERSION}/releases.txt.tmp"

  while [ "${day}" != "${tomorrow}" ]; do

    release="$(echo ${day} | tr -d '-' )"

    if [[ "${ODOO_VERSION}" == '9.0' ]]; then
      basename="odoo_${ODOO_VERSION}c.${release}"
    else
      basename="odoo_${ODOO_VERSION}.${release}"
    fi

    url="http://nightly.odoo.com/${ODOO_VERSION}/nightly/deb/${basename}_amd64.changes"
    sha1sum=$(curl -s "${url}" \
      | grep '_all.deb' \
      | head -n 1 \
      | awk '{ print $1 }' \
    )

    if [[ "${sha1sum}" != "" ]]; then
      # found checksum
      echo "${release}:${sha1sum}" >> "${ODOO_VERSION}/releases.txt.tmp"
    fi

    epoch=$(date -j -f "${fmt_date}" ${day} "+%s")
    next=$((${epoch} + 86400))
    day=$(date -j -f "%s" ${next} "+${fmt_date}")

  done

  echo "generating ${ODOO_VERSION}/releases.txt..."
  paste "${ODOO_VERSION}/releases.txt" "${ODOO_VERSION}/releases.txt.tmp" | sort -r | uniq > "${ODOO_VERSION}/releases.txt.out"
  mv "${ODOO_VERSION}/releases.txt.out" "${ODOO_VERSION}/releases.txt"

done
