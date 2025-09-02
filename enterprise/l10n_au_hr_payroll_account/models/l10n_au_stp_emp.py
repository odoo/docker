from odoo import api, fields, models


class L10nAuSTPEmp(models.Model):
    _name = "l10n_au.stp.emp"
    _description = "STP Employee"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True)
    payslip_ids = fields.Many2many(
        "hr.payslip", string="Payslip", compute="_compute_ytd")
    ytd_balance_ids = fields.Many2many(
        "l10n_au.payslip.ytd", string="YTD Balances", compute="_compute_ytd")
    currency_id = fields.Many2one(
        "res.currency", related="stp_id.currency_id", readonly=True)
    stp_id = fields.Many2one(
        "l10n_au.stp", string="Single Touch Payroll")
    ytd_gross = fields.Monetary("Total Gross", compute="_compute_ytd")
    ytd_tax = fields.Monetary("Total Tax", compute="_compute_ytd")
    ytd_super = fields.Monetary("Total Super", compute="_compute_ytd")
    ytd_rfba = fields.Monetary("Total RFBA", compute="_compute_ytd")
    ytd_rfbae = fields.Monetary("Total RFBA-E", compute="_compute_ytd")

    @api.depends("employee_id", "stp_id.start_date", "stp_id.end_date")
    def _compute_ytd(self):
        for emp in self:
            emp.payslip_ids = emp.employee_id.slip_ids.filtered(lambda p: p.date_from >= emp.stp_id.start_date and p.date_from <= emp.stp_id.end_date)
            emp.ytd_balance_ids = self.env['l10n_au.payslip.ytd'].search([
                ('employee_id', '=', emp.employee_id.id),
                ('start_date', '=', emp.stp_id.start_date),
            ])
            last_payslip = emp.payslip_ids.sorted("date_from", reverse=True)[:1]
            ytd_vals = last_payslip._get_line_values(["BASIC", "WITHHOLD.TOTAL", "SUPER", "RFBA"], vals_list=['ytd'])
            input_vals = last_payslip._l10n_au_get_ytd_inputs()
            emp.ytd_gross = ytd_vals["BASIC"][last_payslip.id]["ytd"]
            emp.ytd_tax = ytd_vals["WITHHOLD.TOTAL"][last_payslip.id]["ytd"]
            emp.ytd_super = ytd_vals["SUPER"][last_payslip.id]["ytd"]
            rfba_input = input_vals.get(self.env.ref("l10n_au_hr_payroll.input_fringe_benefits_amount"))
            emp.ytd_rfba = rfba_input['amount'] if rfba_input else 0
            rfba_input = input_vals.get(self.env.ref("l10n_au_hr_payroll.input_fringe_benefits_exempt_amount"))
            emp.ytd_rfbae = rfba_input['amount'] if rfba_input else 0
