# How-to

This repo is structured the following way:

- `${ODOO_VERSION}/`
  - `base/`
    - `Dockerfile`: file to build the `${ODOO_VERSION}-base` container image
  - `${ODOO_RELEASE}/`
    - `Dockerfile`: file to build the `${ODOO_VERSION}.${ODOO_RELEASE}` container image taking `${ODOO_VERSION}-base` as a base

This repo contains a few bash scripts to
help you generate docker container images.

`generate_releases.sh` will go to nightly.odoo.com and
grab the available releases and SHA1 checksum and
rebuild the `${ODOO_VERSION}/releases.txt`.

```bash
# all
$ bash generate_releases.sh

# single release
$ bash generate_releases.sh 2016-12-30
```

`generate.sh` will read the `${ODOO_VERSION}/releases.txt` file,
parse the `release:checksum` lines and
generate the `${ODOO_VERSION}/${ODOO_RELEASE}/Dockerfile`.

```bash
# all
$ bash generate.sh

# single release
$ bash generate.sh 2016-12-30
```

`build.sh` is used to build the docker container images locally.

```bash
# all
$ bash build.sh

# single release
$ bash build.sh 2016-12-30
```

There are some auxiliary bash scripts to run docker container locally.

```bash
# start an Odoo release container
$ bash start_container.sh 9.0 2016-11-23
# or
$ bash start_container.sh 9.0 20161123

# open interactive session on the Odoo container
$ bash login.sh 9.0 2016-11-23
# or
$ bash login.sh 9.0 20161123

# stop and destroy
$ bash stop_container.sh 9.0 2016-11-23
# or
$ bash stop_container.sh 9.0 20161123
```
