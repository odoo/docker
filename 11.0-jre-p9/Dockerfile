FROM wongnai/odoo:11.0-20180516

USER root

# Need postgres in backport so that we can export database from odoo web
RUN echo 'deb http://archive.debian.org/debian jessie-backports main' >> /etc/apt/sources.list \
	&& apt-get update \
	&& apt-get -t jessie-backports -y install postgresql-client \
    && apt-get -y install openjdk-8-jre gettext-base git \
    && rm -rf /var/lib/apt/lists/*

USER odoo
