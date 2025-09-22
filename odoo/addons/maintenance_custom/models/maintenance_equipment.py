from odoo import models, fields

class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    assigned_company = fields.Char(
        string="Assigned Company",
        copy=True,
        tracking=True,
    )

    trn_no = fields.Char(
        string="TRN No.",
        copy=True,
        tracking=True,
    )

    project_reference = fields.Char(
        string="Project Reference",
        copy=True,
        tracking=True,
    )

    sla = fields.Char(
        string="SLA",
        copy=True,
        tracking=True,
    )

    client_name = fields.Char(
        string="Client Name",
        copy=True,
        tracking=True,
    )

    phone_no = fields.Char(
        string="Phone No.",
        copy=True,
        tracking=True,
    )

    email = fields.Char(
        string="Email",
        copy=True,
        tracking=True,
    )

    position = fields.Char(
        string="Position",
        copy=True,
        tracking=True,
    )

    account_executive = fields.Many2one(
        "hr.employee",
        string="Account Executive",
        copy=True,
        tracking=True,
    )

    preventive_maintenance_coverage = fields.Selection(
        string="Preventive Maintenance Coverage",
        selection=[
            ('weekly', 'WEEKLY'),
            ('monthly', 'MONTHLY'),
            ('quarterly', 'QUARTERLY'),
        ],
        copy=False,
    )