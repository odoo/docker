#!/bin/bash
# #####
#
# Build Odoo 8.0/9.0/10.0 base+release docker container images.
#
# usage:
#   # all
#   bash build.sh
#
#   # single release
#   bash build.sh 20161230
#
# author: Pedro Salgado <steenzout@ymail.com>
# version: 1.2
#
# #####

ARG_RELEASE="${1}"

for ODOO_VERSION in 8.0 9.0 10.0
do

  echo "building steenzout/odoo:${ODOO_VERSION}-base..."
  docker build -t "steenzout/odoo:${ODOO_VERSION}-base" -f "${ODOO_VERSION}/base/Dockerfile" .

  for line in `cat "${ODOO_VERSION}/releases.txt"`
  do

    IFS=':' read -a line_array <<< "$line"
    ODOO_RELEASE="${line_array[0]}"
    ODOO_SHA1SUM="${line_array[1]}"

    if [[ "${ARG_RELEASE}" == "" || "${ARG_RELEASE}" == "${ODOO_RELEASE}" ]]; then

      echo "building steenzout/odoo:${ODOO_VERSION}.${ODOO_RELEASE}..."
      cd "${ODOO_VERSION}/${ODOO_RELEASE}/"
      docker build -t "steenzout/odoo:${ODOO_VERSION}.${ODOO_RELEASE}" -f "Dockerfile" .
      cd ../../

    fi

  done
done
