About this fork
======

This is a fork of odoo docker official image. We make the fork for two reasons till now:
* We want to use more recent nighty odoo builds and officla repository is updated only after some months
* On default odoo, as there are no locales, when creating a new database and loading language  (for eg. es_ar), no correct language info is loaded (for eg date format). So we add a modification to install es_AR locale and some others. We could make this modification on our adhoc odoo container modificacion because we can' achieve to install a newlocale on jessie, so we change linux distribution to ubuntu 14:04 and then add "locale-gen es_AR.UTF-8" to install locales

About this Repo
======

This is the Git repo of the official Docker image for [Odoo](https://registry.hub.docker.com/_/odoo/). See the Hub page for the full readme on how to use the Docker image and for information regarding contributing and issues.

The full readme is generated over in [docker-library/docs](https://github.com/docker-library/docs), specifically in [docker-library/docs/odoo](https://github.com/docker-library/docs/tree/master/odoo).
