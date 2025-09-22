from odoo import models, fields


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    tsd_duty = fields.Many2one(
        "hr.employee",
        string="TSD Duty",
        copy=True,
        tracking=True,
    )

    start_date = fields.Datetime(
        string="Planned Start Date",
        copy=True,
        tracking=True,
    )

    end_date = fields.Datetime(
        string="Planned End Date",
        copy=True,
        tracking=True,
    )

    assigned_engineer = fields.Many2one(
        "hr.employee",
        string="Assigned Engineer",
        copy=True,
        tracking=True,
    )

    companion = fields.Many2one(
        "hr.employee",
        string="Companion",
        copy=True,
        tracking=True,
    )

    equipment_ids = fields.Many2many(
        "maintenance.equipment",
        "helpdesk_ticket_maintenance_equipment_rel",  # relation table
        "helpdesk_ticket_id",  # left column -> matches model name 'helpdesk.ticket'
        "maintenance_equipment_id",  # right column -> matches model name 'maintenance.equipment'
        string="Equipment",
        copy=True,
        tracking=True,
    )


    resolution_note = fields.Text(
        string="Resolution Note",
        copy=True,
        tracking=True,
    )

    attached_files = fields.Binary(
        string="Attached Files",
        copy=True,
        attachment=True,
        tracking=True,
    )

    attached_files_filename = fields.Char(
        string="Filename for Attached Files",
        copy=True,
        tracking=True,
    )

    service_code = fields.Selection(
        selection=[
            ("01", "01 - Break Fix – Customer Initiated"),
            ("02", "02 - Break Fix – Not under MA / Needs approval"),
            ("05", "05 - Assistance (To Customer and/or CE)"),
            ("08", "08 - Preventive Maintenance"),
            ("20", "20 - Machine Installation"),
            ("21", "21 - Machine Relocation"),
            ("22", "22 - Machine Discontinuance"),
            ("37", "37 - Onsite Inventory/Audit Prior MA"),
            ("48", "48 - Account on-Site Standby and Administration (Customer Site)"),
            ("57", "57 - Part Sourcing/Delivery/Travel Time/Housekeeping"),
        ],
        string="Service Code",
        copy=True,
        tracking=True,
    )

# Computed fields (concat values from all linked equipments)
    trn_no = fields.Char(
        string="TRN No.",
        compute="_compute_equipment_details",
        store=True,
        readonly=True,
    )

    category_id = fields.Char(
        string="Category",
        compute="_compute_equipment_details",
        store=True,
        readonly=True,
    )

    equipment_name = fields.Char(
        string="Equipment Name",
        compute="_compute_equipment_details",
        store=True,
        readonly=True,
    )

    serial_no = fields.Char(
        string="Serial No.",
        compute="_compute_equipment_details",
        store=True,
        readonly=True,
    )

    company_id_display = fields.Char(
        string="Company",
        compute="_compute_equipment_details",
        store=True,
        readonly=True,
    )

    warranty_date = fields.Char(
        string="Expiration Date",
        compute="_compute_equipment_details",
        store=True,
        readonly=True,
    )

    active_equipment = fields.Char(
        string="Active",
        compute="_compute_equipment_details",
        store=True,
        readonly=True,
    )


    def _compute_equipment_details(self):
        for ticket in self:
            if ticket.equipment_ids:
                ticket.trn_no = ", ".join(filter(None, ticket.equipment_ids.mapped("trn_no")))
                ticket.category_id = ", ".join(filter(None, ticket.equipment_ids.mapped("category_id.name")))
                ticket.equipment_name = ", ".join(filter(None, ticket.equipment_ids.mapped("name")))
                ticket.serial_no = ", ".join(filter(None, ticket.equipment_ids.mapped("serial_no")))
                ticket.company_id_display = ", ".join(filter(None, ticket.equipment_ids.mapped("company_id.name")))
                ticket.warranty_date = ", ".join(
                    filter(None, [str(x) for x in ticket.equipment_ids.mapped("warranty_date") if x])
                )
                ticket.active_equipment = ", ".join(["Yes" if e.active else "No" for e in ticket.equipment_ids])
            else:
                ticket.trn_no = False
                ticket.category_id = False
                ticket.equipment_name = False
                ticket.serial_no = False
                ticket.company_id_display = False
                ticket.warranty_date = False
                ticket.active_equipment = False
