# How-to

This repo is structured the following way:

- `${ODOO_VERSION}/`
  - `base/`
    - `Dockerfile`: file to build the `${ODOO_VERSION}-base` container image
  - `${ODOO_RELEASE}/`
    - `Dockerfile`: file to build the `${ODOO_VERSION}.${ODOO_RELEASE}` container image taking `${ODOO_VERSION}-base` as a base

This repo contains a few bash scripts to
help you generate docker container images.

`generate.sh` will read the `${ODOO_VERSION}/releases.txt` file,
parse the `release:checksum` lines and
generate the `${ODOO_VERSION}/${ODOO_RELEASE}/Dockerfile`.

```bash
$ bash generate.sh
```

`build.sh` is used to build the docker container images locally.

```bash
$ bash build.sh
```

There are some auxiliary bash scripts to run docker container locally.

```bash
# start an Odoo release container
$ bash start_container.sh 9.0 20161123

# open interactive session on the Odoo container
$ bash login.sh 9.0 20161123

# stop and destroy
$ bash stop_container.sh 9.0 20161123
```
