# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.tools import date_utils, format_list
from odoo.exceptions import ValidationError


class L10nAUPayrollFinalisationWizard(models.TransientModel):
    _name = "l10n_au.payroll.finalisation.wizard"
    _description = "STP Finalisation"

    def _default_fiscal_year(self):
        return self._get_fiscal_year_selection()[0][0]

    name = fields.Char("Name", compute="_compute_name", required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, string="Company", readonly=True)
    abn = fields.Char("ABN", related="company_id.vat")
    branch_code = fields.Char(related="company_id.l10n_au_branch_code")
    bms_id = fields.Char(related="company_id.l10n_au_bms_id")
    date_deadline = fields.Date("Deadline Date", default=lambda self: fields.Date.today(), required=True)
    is_eofy = fields.Boolean("EOFY Declaration", default=False)
    date_start = fields.Date("Date Start", compute="_compute_date_period", required=True)
    date_end = fields.Date("Date End", compute="_compute_date_period", required=True)
    fiscal_year = fields.Selection(selection="_get_fiscal_year_selection", string="Fiscal Year", default=_default_fiscal_year, required=True)
    l10n_au_payroll_finalisation_emp_ids = fields.One2many(
        "l10n_au.payroll.finalisation.wizard.emp",
        "l10n_au_payroll_finalisation_id",
        compute="_compute_all_employees",
        store=True,
        readonly=False,
        string="Employees",
    )
    responsible_user_id = fields.Many2one("res.users", string="Responsible User", default=lambda self: self.env.company.l10n_au_stp_responsible_id.user_id, required=True)
    finalisation = fields.Boolean("Finalisation", default=True, help="Set it to false to un-finalise the employees.")

    def _get_fiscal_year_selection(self):
        today = fields.Date.today()
        selection = []
        fiscal_start, fiscal_end = date_utils.get_fiscal_year(today, self.env.company.fiscalyear_last_day, int(self.env.company.fiscalyear_last_month))
        for year in range(5):
            start = fiscal_start - date_utils.get_timedelta(year, "year")
            end = fiscal_end - date_utils.get_timedelta(year, "year")
            selection.append((fields.Date.to_string(start), f"{start.strftime('%Y')}/{end.strftime('%y')}"))
        return selection

    @api.depends("date_start", "date_end", "finalisation", "is_eofy", "l10n_au_payroll_finalisation_emp_ids")
    def _compute_name(self):
        for rec in self:
            if not rec.finalisation:
                rec.name = _("Amendment of Prior Finalisation - %s", (dict(self._get_fiscal_year_selection())[rec.fiscal_year]))
            if rec.is_eofy and rec.finalisation:
                rec.name = _("EOFY Finalisation - %s", (dict(self._get_fiscal_year_selection())[rec.fiscal_year]))
            elif not rec.is_eofy:
                employees = rec.l10n_au_payroll_finalisation_emp_ids.employee_id
                message = self.env._("Individual Finalisation") if rec.finalisation else self.env._("Individual Amendment of Prior Finalisation")
                rec.name = "%s - %s" % (message, format_list(self.env, employees.mapped('name')))

    @api.depends("is_eofy", "fiscal_year")
    def _compute_date_period(self):
        for rec in self:
            rec.date_start = fields.Date.to_date(rec.fiscal_year)
            if rec.is_eofy:
                rec.date_end = rec.date_start + date_utils.get_timedelta(1, "year") - date_utils.get_timedelta(1, "day")
            else:
                rec.date_end = fields.Date.today()

    @api.depends("company_id", "is_eofy")
    def _compute_all_employees(self):
        for rec in self:
            if not rec.is_eofy:
                continue
            employees_to_add = (
                rec.env["hr.employee"]
                .with_context(active_test=False)
                .search(
                    [
                        ("id", "not in", rec.l10n_au_payroll_finalisation_emp_ids.employee_id.ids),
                        ("company_id", "=", rec.company_id.id),
                        "|",
                        ("departure_date", ">=", rec.date_start),
                        ("departure_date", "=", False),
                    ]
                )
            )
            rec.update(
                {
                    "l10n_au_payroll_finalisation_emp_ids": [
                        Command.create({"employee_id": emp.id})
                        for emp in employees_to_add
                    ]
                }
            )

    @api.constrains("date_start", "is_eofy")
    def _check_fiscal_year(self):
        for rec in self:
            fiscal_start, _ = date_utils.get_fiscal_year(fields.Date.today(), self.env.company.fiscalyear_last_day, int(self.env.company.fiscalyear_last_month))
            if not rec.is_eofy and rec.date_start < fiscal_start:
                raise ValidationError(_("Past finalisations can only be done for the complete year please select EOFY finalisation."))

    def submit_to_ato(self):
        self.ensure_one()
        stp = self.env["l10n_au.stp"].create({
            "name": self.name,
            "company_id": self.company_id.id,
            "payevent_type": "update",
            "is_finalisation": self.finalisation,
            "is_unfinalisation": not self.finalisation,
            "start_date": self.date_start,
            "end_date": self.date_end,
            "l10n_au_stp_emp": [
                Command.create({
                    "employee_id": emp.employee_id.id,
                })
                for emp in self.l10n_au_payroll_finalisation_emp_ids
            ]
        })
        return stp._get_records_action()


class L10nAUPayrollFinalisationEmp(models.TransientModel):
    _name = "l10n_au.payroll.finalisation.wizard.emp"
    _description = "STP Finalisation Employees"

    l10n_au_payroll_finalisation_id = fields.Many2one("l10n_au.payroll.finalisation.wizard", string="Finalisation Wizard", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="l10n_au_payroll_finalisation_id.company_id", string="Company", store=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, domain="[('active', 'in', [False, True])]")
    contract_id = fields.Many2one("hr.contract", related="employee_id.contract_id", string="Contract", required=True)
    contract_start_date = fields.Date("Contract Start Date", related="contract_id.date_start", required=True)
    contract_end_date = fields.Date("Contract End Date", related="contract_id.date_end")
    contract_active = fields.Boolean("Active", related="contract_id.active")
    ytd_balance_ids = fields.Many2many("l10n_au.payslip.ytd", "YTD Balances", compute="_compute_amounts_to_report")
    payslip_ids = fields.Many2many("hr.payslip", "Payslips", compute="_compute_amounts_to_report")

    @api.depends("employee_id", "l10n_au_payroll_finalisation_id.date_start", "l10n_au_payroll_finalisation_id.date_end")
    def _compute_amounts_to_report(self):
        for rec in self:
            rec.ytd_balance_ids = self.env["l10n_au.payslip.ytd"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("start_date", ">=", rec.l10n_au_payroll_finalisation_id.date_start),
                    ("start_date", "<=", rec.l10n_au_payroll_finalisation_id.date_end),
                ]
            )
            rec.payslip_ids = self.employee_id.slip_ids.filtered_domain(
                [
                    ("date_from", ">=", rec.l10n_au_payroll_finalisation_id.date_start),
                    ("date_from", "<=", rec.l10n_au_payroll_finalisation_id.date_end),
                    ("state", "in", ("done", "paid")),
                ]
            )
