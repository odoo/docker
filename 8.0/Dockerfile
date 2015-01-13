FROM debian:jessie
MAINTAINER Odoo S.A. <info@odoo.com>

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf
RUN apt-get update \
	    && apt-get install -y \
            adduser \
            ca-certificates \
            curl \
            npm \
            python-support \
        && npm install -g less less-plugin-clean-css \
        && ln -s /usr/bin/nodejs /usr/bin/node \
        && curl -o wkhtmltox.deb -SL http://downloads.sourceforge.net/project/wkhtmltopdf/0.12.2/wkhtmltox-0.12.2_linux-jessie-amd64.deb \
        && echo 'b6309d2bc45b6f97ad7f208810d468369a94d5c9 wkhtmltox.deb' | sha1sum -c - \
        && dpkg --force-depends -i wkhtmltox.deb \
        && apt-get -y install -f \
        && rm -rf /var/lib/apt/lists/* wkhtmltox.deb

# Grab gosu for easy step-down from root
RUN gpg --keyserver pgp.mit.edu --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4
RUN curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture)" \
        && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/1.2/gosu-$(dpkg --print-architecture).asc" \
        && gpg --verify /usr/local/bin/gosu.asc \
        && rm /usr/local/bin/gosu.asc \
        && chmod +x /usr/local/bin/gosu

# Install Odoo
ENV ODOO_VERSION 8.0
ENV ODOO_RELEASE 20141231
RUN curl -o odoo.deb -SL http://nightly.odoo.com/${ODOO_VERSION}/nightly/deb/odoo_${ODOO_VERSION}.${ODOO_RELEASE}_all.deb \
        && dpkg --force-depends -i odoo.deb \
        && apt-get update \
        && apt-get -y install -f --no-install-recommends \
        && rm -rf /var/lib/apt/lists/* odoo.deb

# Retrieve Odoo public key and add Odoo nightly to repo list for further updates
RUN apt-key adv --keyserver pgp.mit.edu --recv-keys 0xdef2a2198183cbb5 \
        && echo "deb http://nightly.odoo.com/${ODOO_VERSION}/nightly/deb/ ./" >> /etc/apt/sources.list

# Run script and Odoo configuration file
COPY ./run.sh /
COPY ./openerp-server.conf /etc/odoo/

# Mount /var/lib/odoo to allow restoring filestore
VOLUME ["/var/lib/odoo"]

CMD ["/run.sh"]
