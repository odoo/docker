ARG version=16
ARG image=odoo:${version}
FROM ${image}

# Install testing requirements
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium && \
    rm -rf /var/lib/apt/lists/*
RUN pip3 install websocket-client
USER odoo
