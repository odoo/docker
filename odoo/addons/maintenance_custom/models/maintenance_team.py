from odoo import fields, models

class MaintenanceTeam(models.Model):
    _inherit = "maintenance.team"

    custom_team_members = fields.Many2many(
        "hr.employee",
        "custom_hr_employee_maintenance_team_rel",  # relation table
        "maintenance_team_id",                 # column for maintenance team
        "employee_id",                         # column for employee
        string="Team Members",
        copy=True,
    )
