# Build the Odoo 20.0 deb from the odoo/odoo 20.0 branch, the same way
# Odoo's setup/package.py builds its nightlies: prepend a changelog entry
# versioned <series>.<YYYYMMDD> and run dpkg-buildpackage.  The date is
# the commit date of the checked-out source, so the version reads like a
# nightly (e.g. 20.0.20260923) for anything that parses it.
#
# ODOO_REF pins the source (branch, tag or commit); the default follows
# the 20.0 branch head.
FROM ubuntu:noble AS odoo-deb

ARG ODOO_REF=20.0

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        debhelper \
        dh-python \
        dpkg-dev \
        fakeroot \
        git \
        python3 \
        python3-setuptools \
        rsync \
    && rm -rf /var/lib/apt/lists/*

RUN git init -q /build/odoo \
    && git -C /build/odoo fetch -q --depth 1 https://github.com/odoo/odoo.git "${ODOO_REF}" \
    && git -C /build/odoo checkout -q FETCH_HEAD \
    && cd /build/odoo \
    && tstamp="$(git log -1 --format=%cd --date=format-local:%Y%m%d)" \
    && tfull="$(date -u -R)" \
    && series="$(python3 -c 'import runpy; print(runpy.run_path("odoo/release.py")["series"])')" \
    && sed -i "1i odoo (${series}.${tstamp}) stable; urgency=low\n\n  * ${series}\n\n -- Odoo Bot <info@odoo.com>  ${tfull}\n" debian/changelog \
    && dpkg-buildpackage -rfakeroot -uc -us -b \
    && mv /build/odoo_${series}.${tstamp}_all.deb /build/odoo.deb \
    && rm -rf /build/odoo

FROM ubuntu:noble
LABEL maintainer="Odoo S.A. <info@odoo.com>"

SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Generate locale C.UTF-8 for postgres and general locale data
ENV LANG=en_US.UTF-8

# Retrieve the target architecture to install the correct wkhtmltopdf package
ARG TARGETARCH

# Install some deps, lessc and less-plugin-clean-css, and wkhtmltopdf

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        dirmngr \
        fonts-noto-cjk \
        gnupg \
        libssl-dev \
        node-less \
        npm \
        python3-magic \
        python3-num2words \
        python3-odf \
        python3-pdfminer \
        python3-pip \
        python3-phonenumbers \
        python3-pyldap \
        python3-qrcode \
        python3-renderpm \
        python3-setuptools \
        python3-slugify \
        python3-vobject \
        python3-watchdog \
        python3-xlrd \
        python3-xlwt \
        xz-utils && \
    if [ -z "${TARGETARCH}" ]; then \
        TARGETARCH="$(dpkg --print-architecture)"; \
    fi; \
    WKHTMLTOPDF_ARCH=${TARGETARCH} && \
    case ${TARGETARCH} in \
    "amd64") WKHTMLTOPDF_ARCH=amd64 && WKHTMLTOPDF_SHA=967390a759707337b46d1c02452e2bb6b2dc6d59  ;; \
    "arm64")  WKHTMLTOPDF_SHA=90f6e69896d51ef77339d3f3a20f8582bdf496cc  ;; \
    "ppc64le" | "ppc64el") WKHTMLTOPDF_ARCH=ppc64el && WKHTMLTOPDF_SHA=5312d7d34a25b321282929df82e3574319aed25c  ;; \
    esac \
    && curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.jammy_${WKHTMLTOPDF_ARCH}.deb \
    && echo ${WKHTMLTOPDF_SHA} wkhtmltox.deb | sha1sum -c - \
    && apt-get install -y --no-install-recommends ./wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/* wkhtmltox.deb

# install latest postgresql-client
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ noble-pgdg main' > /etc/apt/sources.list.d/pgdg.list \
    && GNUPGHOME="$(mktemp -d)" \
    && export GNUPGHOME \
    && repokey='B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8' \
    && gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "${repokey}" \
    && gpg --batch --armor --export "${repokey}" > /etc/apt/trusted.gpg.d/pgdg.gpg.asc \
    && gpgconf --kill all \
    && rm -rf "$GNUPGHOME" \
    && apt-get update  \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -f /etc/apt/sources.list.d/pgdg.list \
    && rm -rf /var/lib/apt/lists/*

# Install rtlcss (on Debian buster)
RUN npm install -g rtlcss

# Install Odoo
# Odoo has not published a 20.0 nightly deb (nor an official odoo:20.0
# image) yet, so the deb is built from source in the odoo-deb stage above.
ENV ODOO_VERSION=20.0
COPY --from=odoo-deb /build/odoo.deb /tmp/odoo.deb
RUN apt-get update \
    && apt-get -y install --no-install-recommends /tmp/odoo.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/odoo.deb

# Copy entrypoint script and Odoo configuration file
COPY ./entrypoint.sh /
COPY ./odoo.conf /etc/odoo/

# Set permissions and Mount /var/lib/odoo to allow restoring filestore and /mnt/extra-addons for users addons
RUN chown odoo /etc/odoo/odoo.conf \
    && mkdir -p /mnt/extra-addons \
    && chown -R odoo /mnt/extra-addons
VOLUME ["/var/lib/odoo", "/mnt/extra-addons"]

# Expose Odoo services
EXPOSE 8069 8071 8072

# Set the default config file
ENV ODOO_RC=/etc/odoo/odoo.conf

COPY wait-for-psql.py /usr/local/bin/wait-for-psql.py

# Set default user when running the container
USER odoo

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]
