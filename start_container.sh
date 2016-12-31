#!/bin/bash
# #####
#
# Start an Odoo container.
#
# usage:
#
#   bash start_container.sh 9.0 20160101
#
# author: Pedro Salgado <steenzout@ymail.com>
# version: 1.2
#
# #####


ODOO_VERSION="${1}"
ODOO_RELEASE=$(echo "${2}" | tr -d '-')


validation() {
  : "${ODOO_VERSION:?first argument needs to be set to the Odoo version (8.0, 9.0 or 10.0).}"
  : "${ODOO_RELEASE:?second argument needs to be set to the Odoo release (e.g. 20160101).}"
}


validation

IMAGE_ODOO="steenzout/odoo:${ODOO_VERSION}.${ODOO_RELEASE}"

docker run \
  -h web \
  --name "odoo.${ODOO_VERSION}_${ODOO_RELEASE}" \
  -p 127.0.0.1:8069:8069 \
  -td \
  "${IMAGE_ODOO}"
