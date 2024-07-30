from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    installer_setup_protocols_ids = fields.One2many(
        "openems.setup_protocol", "installer_id", "Installed OpenEMS Edge"
    )
    customer_setup_protocols_ids = fields.One2many(
        "openems.setup_protocol", "customer_id", "Owner of OpenEMS Edge"
    )
