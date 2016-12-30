#!/bin/bash
# #####
#
# Generate Odoo release specific Dockerfiles.
#
# author: Pedro Salgado <steenzout@ymail.com>
# version: 1.0
#
# #####

for ODOO_VERSION in 8.0 9.0 10.0
do

  for line in `cat "${ODOO_VERSION}/releases.txt"`
  do

    IFS=':' read -a line_array <<< "$line"
    ODOO_RELEASE="${line_array[0]}"
    ODOO_SHA1SUM="${line_array[1]}"

    mkdir -p "${ODOO_VERSION}/${ODOO_RELEASE}" || true

    echo "generating ${ODOO_VERSION}/${ODOO_RELEASE}/vars.env..."
    eval "cat > ${ODOO_VERSION}/${ODOO_RELEASE}/vars.env << EOF
ODOO_RELEASE=${ODOO_RELEASE}
ODOO_SHA1SUM=${ODOO_SHA1SUM}
ODOO_VERSION=${ODOO_VERSION}
EOF"

    echo "generating ${ODOO_VERSION}/${ODOO_RELEASE}/Dockerfile..."
    source "${ODOO_VERSION}/${ODOO_RELEASE}/vars.env"
    eval "cat > ${ODOO_VERSION}/${ODOO_RELEASE}/Dockerfile << EOF
$(cat ${ODOO_VERSION}/Dockerfile.release)
EOF"

  done
done
