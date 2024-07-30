# Copyright 2013 Nicolas Bessi (Camptocamp SA)
# Copyright 2014 Agile Business Group (<http://www.agilebg.com>)
# Copyright 2015 Grupo ESOC (<http://www.grupoesoc.es>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Partner first name and last name",
    "summary": "Split first name and last name for non company partners",
    "version": "16.0.1.0.3",
    "author": "Camptocamp, "
    "Grupo ESOC Ingeniería de Servicios, "
    "Tecnativa, "
    "LasLabs, "
    "ACSONE SA/NV, "
    "DynApps NV, "
    "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "maintainer": "Camptocamp, Acsone",
    "category": "Extra Tools",
    "website": "https://github.com/OCA/partner-contact",
    "depends": ["base_setup"],
    "post_init_hook": "post_init_hook",
    "data": [
        "views/base_config_view.xml",
        "views/res_partner.xml",
        "views/res_user.xml",
    ],
    "auto_install": False,
    "installable": True,
}
