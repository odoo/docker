FROM quay.io/opusvl/odoo:testing_improvements
MAINTAINER Peter Alabaster <peter.alabaster@opusvl.com>

# Install missing system & pip dependencies for runbot module
RUN apt-get update && apt-get install -y \
    libfreetype6-dev libpng12-dev libxft-dev python-dev python-pip && \
        pip install matplotlib
