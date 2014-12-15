FROM debian:wheezy
MAINTAINER Odoo S.A. <info@odoo.com>

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN apt-get update \
	    && apt-get install -y \
            ca-certificates \
            wget \
            adduser \
            python-support \
        && wget -O - https://deb.nodesource.com/setup | bash - \
        && apt-get -y install nodejs \
        && npm install -g less less-plugin-clean-css \
        && wget http://downloads.sourceforge.net/project/wkhtmltopdf/0.12.1/wkhtmltox-0.12.1_linux-wheezy-amd64.deb \
        && dpkg --force-depends -i wkhtmltox-0.12.1_linux-wheezy-amd64.deb \
        && apt-get -y install -f \
        && rm -f wkhtmltox-0.12.1_linux-wheezy-amd64.deb

ENV ODOO_VERSION 8.0
ENV ODOO_RELEASE 20141209

# Install Odoo
RUN wget http://nightly.odoo.com/${ODOO_VERSION}/nightly/deb/odoo_${ODOO_VERSION}.${ODOO_RELEASE}_all.deb \
        && dpkg --force-depends -i odoo_${ODOO_VERSION}.${ODOO_RELEASE}_all.deb \
        && apt-get -y install -f --no-install-recommends \
        && rm -f odoo_${ODOO_VERSION}.${ODOO_RELEASE}_all.deb

# Retrieve Odoo public key, add Odoo nightly to repo list for further updates
RUN wget -O - https://nightly.odoo.com/odoo.key | apt-key add - \
        && echo "deb http://nightly.odoo.com/${ODOO_VERSION}/nightly/deb/ ./" >> /etc/apt/sources.list

# Run script
COPY run.sh /run.sh
RUN chmod u+x /run.sh

# Mount /var/lib/odoo to allow restoring filestore
VOLUME ["/var/lib/odoo"]

CMD ["/run.sh"]
