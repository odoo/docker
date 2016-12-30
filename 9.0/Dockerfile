FROM debian:jessie
MAINTAINER Odoo S.A. <info@odoo.com>

ENV ODOO_VERSION 9.0

# Set the default config file
ENV OPENERP_SERVER /etc/odoo/openerp-server.conf

ENV WKHTMLTOX_SHA1SUM 40e8b906de658a2221b15e4e8cd82565a47d7ee8
ENV WKHTMLTOX_VERSION 0.12.1.2


# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN set -x; \
        apt-get update \
        && apt-get install -y --no-install-recommends \
            ca-certificates \
            curl \
            node-less \
            python-gevent \
            python-pip \
            python-pyinotify \
            python-renderpm \
            python-support \
        && curl -o wkhtmltox.deb -SL "http://nightly.odoo.com/extra/wkhtmltox-${WKHTMLTOX_VERSION}_linux-jessie-amd64.deb" \
        && echo "${WKHTMLTOX_SHA1SUM} wkhtmltox.deb" | sha1sum -c - \
        && dpkg --force-depends -i wkhtmltox.deb \
        && apt-get -y install -f --no-install-recommends \
        && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false -o APT::AutoRemove::SuggestsImportant=false npm \
        && rm -rf /var/lib/apt/lists/* wkhtmltox.deb \
        && pip install psycogreen==1.0
