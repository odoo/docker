from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    branding_partner_id = fields.Many2one("res.partner", string="Branding Partner")
    global_role = fields.Selection(
        [
            ("admin", "Admin"),
            ("installer", "Installer"),
            ("owner", "Owner"),
            ("guest", "Guest"),
        ],
        default="guest",
        required=True,
    )
    device_role_ids = fields.One2many(
        "openems.device_user_role", "user_id", string="Roles"
    )
    alerting_settings = fields.One2many(
        "openems.alerting", "user_id", string="Alerting"
    )
    openems_language = fields.Selection(
        [
            ("EN", "English"),
            ("DE", "German"),
            ("CZ", "Czech"),
            ("NL", "Dutch"),
            ("ES", "Spanish"),
            ("FR", "French"),
            ("HU", "Hungarian"),
            ("JA", "Japanese"),
        ],
        default="DE",
        required=True,
    )
