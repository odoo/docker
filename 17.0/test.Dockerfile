ARG version=17
ARG image=odoo:${version}
FROM ${image}

# Install testing requirements
USER root
RUN curl -o google-chrome-stable_current_amd64.deb -sSL https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        ./google-chrome-stable_current_amd64.deb \
        python3-websocket \
    && rm -rf /var/lib/apt/lists/* ./google-chrome-stable_current_amd64.deb
USER odoo
