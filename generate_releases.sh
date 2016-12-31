#!/bin/bash
# #####
#
# Generate Odoo release.txt files.
#
# author: Pedro Salgado <steenzout@ymail.com>
# version: 1.0
#
# #####

fmt_date='%Y-%m-%d'
today=`date "+${fmt_date}"`

for ODOO_VERSION in 8.0 9.0 10.0
do

  if [[ "${ODOO_VERSION}" == "8.0" ]]; then
    day=2014-11-28
  elif [[ "${ODOO_VERSION}" == "9.0" ]]; then
    day=2016-01-01
  elif [[ "${ODOO_VERSION}" == "10.0" ]]; then
    day=2016-10-05
  else
    echo "[ERROR] unknown version ${ODOO_VERSION}"
    exit 1
  fi

  echo "collecting SHA1 checksums for ${ODOO_VERSION} starting at ${day}..."
  rm "${ODOO_VERSION}/releases.txt.tmp"

  while [ "${day}" != "${today}" ]; do

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
    day=$(date -j -f "%s" $next "+${fmt_date}")

  done

  echo "generating ${ODOO_VERSION}/releases.txt..."
  cat "${ODOO_VERSION}/releases.txt.tmp" | sort -r > "${ODOO_VERSION}/releases.txt"
  rm "${ODOO_VERSION}/releases.txt.tmp"

done
