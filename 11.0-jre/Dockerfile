FROM odoo:11.0

USER root

RUN apt-get update && \
    apt-get -y install openjdk-8-jre && \
    rm -rf /var/lib/apt/lists/*

USER odoo
