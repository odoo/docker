FROM debian:stretch-slim
ENV LANG C.UTF-8
# Needed to download requirements.txt from github
ENV ODOOVER 11.0
USER root
RUN set -x ; \
    apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    libldap2-dev \
    libsasl2-dev \
    libxslt1-dev \
    node-less \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    virtualenv \
    && curl -sSL https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2 -o phantomjs.tar.bz2 \
    && tar xvfO phantomjs.tar.bz2 phantomjs-2.1.1-linux-x86_64/bin/phantomjs > /usr/local/bin/phantomjs \
    && rm phantomjs.tar.bz2 \
    && chmod +x /usr/local/bin/phantomjs \
    && curl -sSL https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.stretch_amd64.deb -o /tmp/wkhtml.deb \
    && dpkg --force-depends -i /tmp/wkhtml.deb \
    && apt-get install -y -f --no-install-recommends \
    && rm /tmp/wkhtml.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1000 odoo \
    && useradd -u 1000 -g odoo odoo \
    && mkdir /home/odoo \
    && chown -R odoo:odoo /home/odoo
USER odoo
ADD --chown=odoo:odoo https://raw.githubusercontent.com/odoo/odoo/${ODOOVER}/requirements.txt /home/odoo/requirements.txt
RUN ["/bin/bash", "-c", "virtualenv -p python3 /home/odoo/odoovenv && source /home/odoo/odoovenv/bin/activate && pip install --no-cache-dir -r /home/odoo/requirements.txt"]
