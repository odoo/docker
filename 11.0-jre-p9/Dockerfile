FROM wongnai/odoo:11.0-20180516

USER root

RUN apt-get update \
    && apt-get -y install openjdk-8-jre gettext-base git postgresql-client \
    && rm -rf /var/lib/apt/lists/*

USER odoo
