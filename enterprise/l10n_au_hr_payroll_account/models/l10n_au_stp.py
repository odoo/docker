# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from lxml import etree
from datetime import date, timedelta
from collections import defaultdict
import re
import logging

from odoo import api, fields, models, _
from odoo.tools.misc import file_path
from odoo.tools import float_compare, float_round, date_utils, groupby
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

EMPLOYEE_REQUIRED_FIELDS = [
    "l10n_au_tfn", "name", "birthday",
    "private_street", "private_city", "private_state_id", "private_zip",
    "private_country_id", "private_email", "private_phone",
]

COMPANY_REQUIRED_FIELDS = [
    "vat", "l10n_au_bms_id", "l10n_au_stp_responsible_id", "email", "phone", "zip"
]


def strip_phonenumber(phone: str):
    return ''.join(re.findall(r'(\d+)', phone))


class L10nAuSTP(models.Model):
    _name = "l10n_au.stp"
    _description = "Single Touch Payroll"
    _order = "create_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _default_start_date(self):
        start, _ = date_utils.get_fiscal_year(
                fields.Date.today(),
                self.env.company.fiscalyear_last_day,
                int(self.env.company.fiscalyear_last_month),
            )
        return start

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    payslip_batch_id = fields.Many2one("hr.payslip.run", string="Payslip Batch")
    payslip_ids = fields.Many2many("hr.payslip", string="Payslip")
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        readonly=True,
    )
    payevent_type = fields.Selection(
        [("submit", "Submit"), ("update", "Update")],
        string="Submission Type",
        required=True,
        default="submit",
        help="""Submission type of the report
                Submit: Submit a new report
                Update: Update an Employee Record from a past report""",
    )
    ffr = fields.Boolean(
        string="Full File Replacement",
        help="Indicates if this report should replace the previous report with the same transaction identifier")
    is_replaced = fields.Boolean("Is Replaced")
    file_replacement_message = fields.Char(readonly=True, compute="_compute_file_replacement_message")
    is_latest = fields.Boolean("Is Latest", compute="_compute_is_latest", store=False)
    previous_report_id = fields.Many2one(
        "l10n_au.stp", string="Previous Report",
        help="Report which you are updating")
    submit_date = fields.Date(
        string="Submit Date",
        compute="_compute_submit_date",
        store=True,
        readonly=False,
        help="Enter manual submit date if you want to submit the report at a particular date")
    submission_id = fields.Char(
        string="Submission ID",
        readonly=True,
        help="Submission ID of the report")
    # XML report fields
    state = fields.Selection([("draft", "Draft"), ("sent", "Submitted")], default="draft")
    xml_file = fields.Binary("XML File", readonly=True, store=True)
    xml_filename = fields.Char()
    xml_validation_state = fields.Selection([
        ("normal", "N/A"),
        ("done", "Valid"),
        ("invalid", "Invalid"),
    ], default="normal")
    error_message = fields.Text("Error Message", readonly=True)
    warning_message = fields.Char(compute="_compute_warning_message")
    l10n_au_stp_emp = fields.One2many("l10n_au.stp.emp", "stp_id", string="Employees")
    is_finalisation = fields.Boolean(readonly=True)
    is_unfinalisation = fields.Boolean(readonly=True)
    start_date = fields.Date("Start Date", inverse="_fiscal_start_date", default=_default_start_date)
    end_date = fields.Date("End Date", compute="_compute_end_date", store=True, readonly=False)
    is_zeroing = fields.Boolean("Zero Out YTD")

    # constraints ffr, cannot be true if type is update
    _sql_constraints = [
        ("ffr", "CHECK(ffr = false OR payevent_type = 'submit')", "Full File Replacement cannot be true if type is 'update'."),
        ("l10n_au_l10n_au_previous_report", "CHECK(previous_report_id != id)", "A report can't update iself.")
    ]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for rec in res:
            rec.activity_schedule(
                "l10n_au_hr_payroll_account.l10n_au_activity_submit_stp",
                user_id=rec.company_id.l10n_au_stp_responsible_id.user_id.id
            )
        return res

    def _fiscal_start_date(self):
        for rec in self:
            if rec.start_date and rec.payevent_type == "update":
                fiscal_year_last_month = int(rec.company_id.fiscalyear_last_month)
                start_year = rec.start_date.year
                # Start is previous year
                if rec.start_date.month <= fiscal_year_last_month:
                    start_year -= 1
                if fiscal_year_last_month == 12:
                    fiscal_year_last_month = 0
                rec.start_date = rec.start_date.replace(day=1, month=fiscal_year_last_month + 1, year=start_year)
                rec.end_date = rec.start_date + timedelta(days=364)

    @api.depends("start_date")
    def _compute_end_date(self):
        for rec in self:
            rec.end_date = rec.start_date + timedelta(days=364)

    @api.depends("payslip_ids", "payslip_batch_id")
    def _compute_currency_id(self):
        for report in self:
            if report.payslip_batch_id:
                report.currency_id = report.payslip_batch_id.currency_id
            else:
                report.currency_id = report.payslip_ids[:1].currency_id

    @api.depends("payslip_batch_id", "payslip_ids", "payevent_type", "is_zeroing", "is_finalisation")
    def _compute_name(self):
        for report in self:
            if report.is_finalisation:
                report.name = report.name
            elif report.is_zeroing:
                report.name = _("Zeroing YTD - %s", report.company_id.name)
            elif report.payevent_type == "update":
                report.name = _("Update Event - %s", report.start_date)
            elif report.payslip_batch_id:
                report.name = report.payslip_batch_id.name
            else:
                period = self.payslip_ids and self.payslip_ids[0]._get_period_name({})
                report.name = _("Out of Cycle Reporting - %s", period)
            if report.ffr:
                report.name += " (FFR)"

    @api.depends("payevent_type", "l10n_au_stp_emp")
    def _compute_submit_date(self):
        for report in self:
            if report.payevent_type == "submit":
                if report.payslip_ids:
                    report.submit_date = report.payslip_batch_id.date_end if report.payslip_batch_id else report.payslip_ids[0].date_to
            elif report.payevent_type == "update":
                if not report.l10n_au_stp_emp:
                    report.submit_date = date.today()
                elif report._is_for_current_fiscal_year():
                    report.submit_date = fields.Date.today()
                else:
                    report.submit_date = report.l10n_au_stp_emp.payslip_ids.sorted("date_from")[-1].date_to

    def _compute_warning_message(self):
        for report in self:
            company_warnings, user_warnings = [], []
            company = self.company_id
            user = self.company_id.l10n_au_stp_responsible_id
            for field in COMPANY_REQUIRED_FIELDS:
                if not company[field]:
                    company_warnings.append(company._fields[field].string)
            if user:
                for field in EMPLOYEE_REQUIRED_FIELDS:
                    if not user[field]:
                        user_warnings.append(user._fields[field].string)
            message = ""
            if company_warnings:
                message += "\n  ・ ".join(["Missing required company information:"] + company_warnings) + '\n'
            if user_warnings:
                message += "\n  ・ ".join(["Missing required STP Responsible user information:"] + user_warnings)
            report.warning_message = message

    def _compute_file_replacement_message(self):
        for report in self:
            report.file_replacement_message = False
            replacement_report = self.search([("previous_report_id", "=", report.id), ("ffr", "=", True)])
            if report.ffr:
                report.file_replacement_message = _("This report is a Full File Replacement for %s.\n", (report.previous_report_id.name))
            elif replacement_report or (report.is_replaced and report.previous_report_id):
                report.file_replacement_message = _("This submission has been replaced by %s. Please check the new report.", (replacement_report.name))

    def _compute_is_latest(self):
        for report in self:
            report.is_latest = self.search([("state", "=", "sent")], order="id desc", limit=1) == report

    def _get_fiscal_year_start(self):
        self.ensure_one()
        slips = self.payslip_ids if self.payevent_type == 'submit' else self.l10n_au_stp_emp.payslip_ids
        if slips:
            return date_utils.get_fiscal_year(
                slips[0].date_from,
                self.company_id.fiscalyear_last_day,
                int(self.company_id.fiscalyear_last_month),
            )

    @api.constrains("submit_date", "payevent_type")
    def _check_submit_date(self):
        for report in self:
            if report.payevent_type == "update" and report.submit_date and report.l10n_au_stp_emp:
                fiscal_start, fiscal_end = report._get_fiscal_year_start()
                if report.submit_date < fiscal_start or report.submit_date > fiscal_end:
                    raise ValidationError(_("An update event must be submitted within the same fiscal year."))

    def _is_for_current_fiscal_year(self):
        fiscal_start, fiscal_end = self._get_fiscal_year_start()
        return fiscal_start <= fields.Date.today() and fields.Date.today() <= fiscal_end

    @api.constrains('payslip_ids', 'payslip_batch_id')
    def _check_payslip_batches(self):
        for report in self:
            batch = report.payslip_batch_id
            if any(payslip.payslip_run_id != batch for payslip in report.payslip_ids):
                raise ValidationError(
                    _("All payslips must belong to the same batch."))
            if (
                report.payslip_batch_id
                and report.payslip_ids != report.payslip_batch_id.slip_ids
            ):
                raise ValidationError(
                    _("Some payslips from the batch are missing in the report.")
                )

            # Dont allow the same payslip or batch to be submitted twice
            if (
                report.payevent_type == "submit" and not report.ffr and self != report.previous_report_id
                and self.search(
                    [
                        ("payslip_ids", "in", report.payslip_ids.ids),
                        ("payevent_type", "=", "submit"),
                        ("id", "!=", report.id),
                    ]
                ).exists()
            ):
                raise ValidationError(
                    _(
                        "Payslips cannot be submitted to the ATO twice. Please make an update request for corrections."
                    )
                )

    def _get_complex_rendering_data(self):
        payslips_ids = self.payslip_ids if self.payevent_type == 'submit' else self.l10n_au_stp_emp.payslip_ids
        employees = payslips_ids.employee_id

        # == Date and Run Date ==
        if self.payevent_type == "submit":
            run_date = self.payslip_batch_id.payment_report_date or self.create_date
            submit_date = self.payslip_batch_id.payment_report_date or self.create_date.date()
        elif self.payevent_type == "update":
            submit_date = self.submit_date
            run_date = self.create_date

        # == Totals == (may not be reported in an update event)
        line_codes = ["BASIC", "WITHHOLD.TOTAL", "CHILD.SUPPORT", "CHILD.SUPPORT.GARNISHEE", "SUPER", "SUPER.CONTRIBUTION", "OTE", "RFBA", "ETP.WITHHOLD", "ETP.TAXABLE", "ETP.TAXFREE"]
        all_line_values = payslips_ids._get_line_values(line_codes, vals_list=['total', 'ytd'], compute_sum=True)
        extra_data = {
            "PaymentRecordTransactionD": submit_date,
            "MessageTimestampGenerationDt": run_date.isoformat(),
        }
        if self.payevent_type == "submit":
            # These values are reported per pay period. The difference between the YTD in this and the last pay period.
            extra_data.update({
                "PayAsYouGoWithholdingTaxWithheldA": abs(all_line_values["WITHHOLD.TOTAL"]['sum']['total']),
                "TotalGrossPaymentsWithholdingA": all_line_values["BASIC"]['sum']['total'],
                "ChildSupportGarnisheeA": abs(all_line_values["CHILD.SUPPORT.GARNISHEE"]['sum']['total']),  # TODO
                "ChildSupportWithholdingA": abs(round(all_line_values["CHILD.SUPPORT"]['sum']['total'] - all_line_values["CHILD.SUPPORT.GARNISHEE"]['sum']['total'], 2)),
            })
        # Employees extra data reported year to date for the current financial year
        unknown_date = date(1800, 1, 1)
        min_date = date(1950, 1, 1)
        for employee in employees:
            payslips = payslips_ids.filtered(lambda p: p.employee_id == employee)
            if self.payevent_type == "update":
                payslips = payslips.sorted("date_from", reverse=True)[:1]
            if len(payslips) > 1:
                raise ValidationError(_("Employee %s has more than one payslip in the report.", (employee.name)))
            fields_to_compute = [
                "l10n_au_foreign_tax_withheld",
                "l10n_au_exempt_foreign_income",
                "l10n_au_salary_sacrifice_other",
                "l10n_au_salary_sacrifice_superannuation",
                "l10n_au_extra_negotiated_super",
                "l10n_au_extra_compulsory_super",
            ]
            employee_ytd = payslips._l10n_au_get_year_to_date_totals(fields_to_compute=fields_to_compute, zero_amount=self.is_zeroing)
            employee_input_totals = payslips._l10n_au_get_ytd_inputs(zero_amount=self.is_zeroing)

            start_date = max(min_date, employee.first_contract_date) or unknown_date
            remunerations = []
            deductions = []
            for payslip in payslips:
                Remuneration = defaultdict(lambda: False)
                contract_id = payslip.contract_id
                # == Gross, income type, paygw ==
                Remuneration["IncomeStreamTypeC"] = payslip.l10n_au_income_stream_type
                # == Foreign income == (required for FEI, IAA, WHM )
                if payslip.l10n_au_income_stream_type in ["FEI", "IAA", "WHM"]:
                    Remuneration["AddressDetailsCountryC"] = employee.country_id.code.lower()
                Remuneration["IncomeTaxForeignWithholdingA"] = employee_ytd['fields']['l10n_au_foreign_tax_withheld']
                Remuneration["IndividualNonBusinessExemptForeignEmploymentIncomeA"] = employee_ytd['fields']['l10n_au_exempt_foreign_income']
                Remuneration["IncomeTaxPayAsYouGoWithholdingTaxWithheldA"] = abs(employee_ytd['slip_lines']['WITHHOLD.TOTAL']['WITHHOLD.TOTAL'])
                Remuneration["GrossA"] = employee_ytd['slip_lines']['GROSS']['GROSS']
                # == Paid Leave ==
                leave_lines = filter(lambda item: item[0].is_leave, employee_ytd["worked_days"].items())
                Remuneration["PaidLeaveCollection"] = []
                for work_type, leave in leave_lines:
                    Remuneration["PaidLeaveCollection"].append({
                        "TypeC": work_type.l10n_au_work_stp_code,
                        "PaymentA": float_round(leave['amount'], precision_rounding=payslip.currency_id.rounding),
                    })
                # leave_inputs = input_lines_ids.filtered(lambda l: l.input_type_id.l10n_au_payment_type == 'leave')
                leave_inputs = filter(lambda item: item[0].l10n_au_payment_type == 'leave', employee_input_totals.items())
                for input_type, leave in leave_inputs:
                    Remuneration["PaidLeaveCollection"].append({
                        "TypeC": input_type.l10n_au_payroll_code,
                        "PaymentA": float_round(leave['amount'], precision_rounding=payslip.currency_id.rounding),
                    })
                # == Allowance ==
                allowance_lines = filter(
                    lambda item: (
                        item[0].l10n_au_payment_type == "allowance"
                        and item[0].l10n_au_payroll_code not in ["Overtime", False]
                    ),
                    employee_input_totals.items()
                )
                Remuneration["AllowanceCollection"] = []
                for code, allowances in groupby(allowance_lines, lambda item: (item[0].l10n_au_payroll_code, item[0].l10n_au_payroll_code_description)):
                    Remuneration["AllowanceCollection"].append({
                        "TypeC": code[0],
                        "OtherAllowanceTypeDe": code[1] if code[0] == "OD" else False,
                        "EmploymentAllowancesA": sum(allowance[1]['amount'] for allowance in allowances),
                    })
                # == Overtime ==
                overtime_lines = filter(lambda item: item[0].l10n_au_work_stp_code == "T", employee_ytd["worked_days"].items())
                overtime_inputs = filter(lambda item: item[0].l10n_au_payroll_code == "Overtime", employee_input_totals.items())
                Remuneration["OvertimePaymentA"] = sum([line[1]['amount'] for line in overtime_lines] + [ot[1]['amount'] for ot in overtime_inputs])

                # == Bonuses and commissions ==
                bonus_commissions_lines = filter(lambda item: item[0].l10n_au_payroll_code == "Bonus and Commissions", employee_input_totals.items())
                Remuneration["GrossBonusesAndCommissionsA"] = sum(bonus[1]['amount'] for bonus in bonus_commissions_lines)
                # == Directors fees ==
                directors_fee_input_type = self.env.ref("l10n_au_hr_payroll.input_gross_director_fee")
                Remuneration["GrossDirectorsFeesA"] = sum(
                    value["amount"]
                    for _, value in filter(
                        lambda item: item[0] == directors_fee_input_type,
                        employee_input_totals.items(),
                    )
                )
                # == Salary sacrifice ==
                Remuneration["SalarySacrificeCollection"] = []
                if employee_ytd["fields"]["l10n_au_salary_sacrifice_superannuation"]:
                    Remuneration["SalarySacrificeCollection"].append(
                        {"TypeC": "S", "PaymentA": float_round(employee_ytd["fields"]["l10n_au_salary_sacrifice_superannuation"], precision_rounding=payslip.currency_id.rounding)},
                    )
                if employee_ytd["fields"]["l10n_au_salary_sacrifice_other"]:
                    Remuneration["SalarySacrificeCollection"].append(
                        {"TypeC": "O", "PaymentA": float_round(employee_ytd["fields"]["l10n_au_salary_sacrifice_other"], precision_rounding=payslip.currency_id.rounding)},
                    )
                # == Lump Sum (Loempia sum) ==
                lump_sum_input_type = filter(lambda item: item[0].l10n_au_payment_type == 'lump_sum', employee_input_totals.items())
                Remuneration["LumpSumCollection"] = []
                for input_type, lump_sum in lump_sum_input_type:
                    Remuneration["LumpSumCollection"].append({
                        "TypeC": input_type.l10n_au_payroll_code,
                        "PaymentsA": lump_sum['amount'],
                    })
                    if input_type.l10n_au_payroll_code == "E":
                        Remuneration["LumpSumCollection"][-1]["FinancialY"] = lump_sum.get("financial_year")

                # == Termination Payments ==
                Remuneration["EmploymentTerminationPaymentCollection"] = []
                termination_inputs = filter(lambda item: item[0].l10n_au_payment_type == 'etp', employee_input_totals.items())
                for code, input_lines in groupby(termination_inputs, lambda item: item[0].l10n_au_payroll_code):
                    tax_free = sum(line[1]['amount'] for line in input_lines if line[0].l10n_au_etp_type == "excluded")
                    taxable = sum(line[1]['amount'] for line in input_lines if line[0].l10n_au_etp_type != "excluded")
                    Remuneration["EmploymentTerminationPaymentCollection"].append({
                        "IncomePayAsYouGoWithholdingA": abs(employee_ytd['slip_lines']['WITHHOLD']['ETP.WITHHOLD']),
                        "IncomeTaxPayAsYouGoWithholdingTypeC": code,
                        "IncomeD": payslip.paid_date or payslip.date,
                        "IncomeTaxableA": taxable,
                        "IncomeTaxFreeA": tax_free,
                    })

                # == ETP Leaves ==
                etp_leaves, total = payslip._l10n_au_get_leaves_for_withhold()
                if payslip.l10n_au_termination_type == "normal":
                    leave_amount_u = etp_leaves["annual"]["post_1993"] + etp_leaves["long_service"]["post_1993"]
                    if leave_amount_u:
                        Remuneration["PaidLeaveCollection"].append({
                        "TypeC": "U",
                        "PaymentA": float_round(leave_amount_u, precision_rounding=payslip.currency_id.rounding),
                    })
                    lumpsum_amount_t = etp_leaves["annual"]["pre_1993"] + etp_leaves["long_service"]["pre_1993"]
                    if lumpsum_amount_t:
                        Remuneration["LumpSumCollection"].append({
                            "TypeC": "T",
                            "PaymentsA": float_round(lumpsum_amount_t, precision_rounding=payslip.currency_id.rounding),
                        })
                    lumpsum_amount_b = etp_leaves["long_service"]["pre_1978"]
                    if lumpsum_amount_b:
                        Remuneration["LumpSumCollection"].append({
                            "TypeC": "B",
                            "PaymentsA": float_round(lumpsum_amount_b, precision_rounding=payslip.currency_id.rounding),
                        })
                    assert float_compare(total, leave_amount_u + lumpsum_amount_t + lumpsum_amount_b, precision_rounding=payslip.currency_id.rounding) == 0
                else:
                    # In case of genuine redundancy all are type R
                    if total:
                        Remuneration['LumpSumCollection'].append({
                            "TypeC": "R",
                            "PaymentsA": float_round(total, precision_rounding=payslip.currency_id.rounding),
                        })

                remunerations.append(Remuneration)

                # == DEDUCTIONS ==
                if employee_ytd["slip_lines"]["WORK.GIVING"]["WORKPLACE.GIVING"]:
                    deductions.append({
                        "RemunerationTypeC": "W",
                        "RemunerationA": abs(employee_ytd["slip_lines"]["WORK.GIVING"]["WORKPLACE.GIVING"]),
                    })
                child_support_garnishee = employee_ytd["slip_lines"]["CHILD.SUPPORT.GARNISHEE"]["CHILD.SUPPORT.GARNISHEE"]
                if child_support_garnishee:
                    deductions.append({
                        "RemunerationTypeC": "G",
                        "RemunerationA": abs(child_support_garnishee),
                    })
                child_support_deduction = employee_ytd["slip_lines"]["CHILD.SUPPORT"]["CHILD.SUPPORT"]
                if child_support_deduction:
                    deductions.append({
                        "RemunerationTypeC": "D",
                        "RemunerationA": abs(child_support_deduction),
                    })
                deduction_inputs = filter(lambda item: item[0].l10n_au_payment_type == 'deduction', employee_input_totals.items())
                for input_type, deduction in deduction_inputs:
                    deductions.append({
                        "RemunerationTypeC": input_type.l10n_au_payroll_code,
                        "RemunerationA": abs(deduction['amount']),
                    })

                # == Super Contribution ==
                contributions = []
                # OTE Entitlement
                ote = employee_ytd["slip_lines"]['OTE']['OTE']
                if ote:
                    contributions.append({
                        "EntitlementTypeC": "O",
                        "EmployerContributionsYearToDateA": ote,
                    })
                # Non-Resc
                super_liability = employee_ytd["slip_lines"]["SUPER"]["SUPER"] + employee_ytd["fields"]["l10n_au_extra_compulsory_super"]
                if super_liability:
                    contributions.append({
                        "EntitlementTypeC": "L",
                        "EmployerContributionsYearToDateA": round(super_liability, 2),
                    })
                # RESC
                super_contribution = employee_ytd["slip_lines"]["SALARY.SACRIFICE"]["SUPER.CONTRIBUTION"] - employee_ytd["fields"]["l10n_au_extra_compulsory_super"]
                if super_contribution:
                    contributions.append({
                        "EntitlementTypeC": "R",
                        "EmployerContributionsYearToDateA": round(super_contribution, 2),
                    })

                # == Reportable Fringe Benefits ==
                benefits = []
                # rfba = employee_ytd["slip_lines"]["BENEFITS"]["RFBA"]
                rfba_input = filter(lambda item: item[0].code == 'FBT', employee_input_totals.items())
                for input_type, rfba in rfba_input:
                    benefits.append({
                        "FringeBenefitsReportableExemptionC": input_type.l10n_au_payroll_code,
                        "A": rfba['amount'],
                    })

            employee_data = {
                "EmploymentStartD": start_date,
                "Remuneration": remunerations,
                "Deduction": deductions,
                "contributions": contributions,
                "benefits": benefits,
                "contract": contract_id,
                "payslip": payslip,
            }

            extra_data.update({
                employee.id: employee_data
            })

        return extra_data

    def _get_rendering_data(self):
        payees = self.payslip_ids.employee_id if self.payevent_type == 'submit' else self.l10n_au_stp_emp.payslip_ids.employee_id
        is_current_fiscal_year = self._is_for_current_fiscal_year()
        extra_data = self._get_complex_rendering_data()
        company = self.company_id
        sender = self.company_id.l10n_au_stp_responsible_id
        employer = defaultdict(str, {
            "SoftwareInformationBusinessManagementSystemId": company.l10n_au_bms_id,
            "AustralianBusinessNumberId": company.vat.replace(" ", "") or False,
            "WithholdingPayerNumberId": company.l10n_au_wpn_number if not company.vat else "",
            "OrganisationDetailsOrganisationBranchC": company.l10n_au_branch_code,
            "PreviousSoftwareInformationBusinessManagementSystemId": company.l10n_au_previous_bms_id,
            "DetailsOrganisationalNameT": company.name,
            "PersonUnstructuredNameFullNameT": sender.name,
            "ElectronicMailAddressT": sender.private_email,
            "TelephoneMinimalN": strip_phonenumber(sender.private_phone),
            "PostcodeT": company.zip,
            "CountryC": company.country_id.code.lower(),
            "PaymentRecordTransactionD": extra_data["PaymentRecordTransactionD"],
            "InteractionRecordCt": len(payees),
            "MessageTimestampGenerationDt": extra_data["MessageTimestampGenerationDt"],
            "InteractionTransactionId": "",  # filled later
            "AmendmentI": "true" if self.ffr else "false",
            "SignatoryIdentifierT": sender.name,
            "SignatureD": date.today(),
            "StatementAcceptedI": "true",
        })
        if self.payevent_type == "submit":
            employer.update({
                "PayAsYouGoWithholdingTaxWithheldA": extra_data["PayAsYouGoWithholdingTaxWithheldA"],
                "TotalGrossPaymentsWithholdingA": extra_data["TotalGrossPaymentsWithholdingA"],
                "ChildSupportGarnisheeA": extra_data["ChildSupportGarnisheeA"],
                "ChildSupportWithholdingA": extra_data["ChildSupportWithholdingA"],
            })

        intermediary = defaultdict(str)
        intermediary_id = False
        if intermediary_id:
            intermediary.update({
                "AustralianBusinessNumberId": intermediary_id.vat,
                "PersonUnstructuredNameFullNameT": intermediary_id.name,
                "ElectronicMailAddressT": intermediary_id.email,
                "TelephoneMinimalN": strip_phonenumber(intermediary_id.phone),
                "SignatoryIdentifierT": intermediary_id.name,
                "SignatureD": False,
                "StatementAcceptedI": False,
            })
        employees = []
        for employee in payees:
            # For update it should be the last payslip of the pay period
            payslip = extra_data[employee.id]["payslip"]
            start_date = payslip.date_from
            end_date = payslip.date_to
            if self.payevent_type == "update":
                # For update events, the start date is the submission date for the current fiscal year
                # and the last payrun date for the previous fiscal years. End date is the same as start
                # for update events.
                end_date = start_date
                if is_current_fiscal_year:
                    start_date = self.submit_date

            values = defaultdict(str, {
                "TaxFileNumberId": employee.l10n_au_tfn,
                "AustralianBusinessNumberId": employee.l10n_au_abn.replace(" ", "") if employee.l10n_au_abn else "",
                "EmploymentPayrollNumberId": employee.l10n_au_payroll_id or str(employee.id),
                "PreviousPayrollIDEmploymentPayrollNumberId": employee.l10n_au_previous_payroll_id,
                "FamilyNameT": ' '.join(employee.name.split(' ')[1:]),
                "GivenNameT": employee.name.split(' ')[0],
                "OtherGivenNameT": employee.l10n_au_other_names,
                "Dm": employee.birthday.day,
                "M": employee.birthday.month,
                "Y": employee.birthday.year,
                "Line1T": employee.private_street,
                "Line2T": employee.private_street2,
                "LocalityNameT": employee.private_city,
                "StateOrTerritoryC": employee.private_state_id.code,
                "PostcodeT": employee.private_zip,
                "CountryC": employee.private_country_id.code.lower() if employee.private_country_id else False,
                "ElectronicMailAddressT": employee.private_email,
                "TelephoneMinimalN": strip_phonenumber(employee.private_phone),
                "EmploymentStartD": extra_data[employee.id]["EmploymentStartD"],
                "EmploymentEndD": payslip.contract_id.date_end or False,
                "PaymentBasisC": employee.l10n_au_employment_basis_code,
                "CessationTypeC": payslip.contract_id.l10n_au_cessation_type_code,
                "TaxTreatmentC": employee.l10n_au_tax_treatment_code,
                "TaxOffsetClaimTotalA": employee.l10n_au_nat_3093_amount,
                "StartD": start_date,
                "EndD": end_date,
                "RemunerationPayrollEventFinalI": "true" if self.is_finalisation else "false",
                # Remuneration collection
                "Remuneration": extra_data[employee.id]["Remuneration"],
                # Deductions
                "Deduction": extra_data[employee.id]["Deduction"],
                # Super Contributions
                "SuperannuationContributionCollection": extra_data[employee.id]["contributions"],
                # Fringe Benefits
                "IncomeFringeBenefitsReportableCollection": extra_data[employee.id]["benefits"],
            })
            employees.append(values)

        # sequence at the end to avoid generating if there was an error
        self.submission_id = self.env['ir.sequence'].next_by_code("stp.transaction")
        employer["InteractionTransactionId"] = self.submission_id
        return employer, employees, intermediary

    @staticmethod
    def _prettify_validate_xml(report, schema_file_name):
        root = etree.fromstring(report, parser=etree.XMLParser(remove_blank_text=True, resolve_entities=False))
        xml_string = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=False)
        payevent_xsd_root = etree.parse(file_path(f"l10n_au_hr_payroll_account/data/{schema_file_name}.xsd"))
        payevent_schema = etree.XMLSchema(payevent_xsd_root)
        try:
            root = etree.fromstring(xml_string)
            payevent_schema.assertValid(root)
            error = ""
        except etree.DocumentInvalid as err:
            error = str(err)
            _logger.error(error)

        return xml_string, error

    def action_generate_xml(self):
        self.ensure_one()
        self._check_stp_fields()
        self._check_payslips()
        self.xml_filename = '%s-PAYEVNT.0004.xml' % (self.name)
        employer, employees, intermediary = self._get_rendering_data()
        delimiter = '<Record_Delimiter DocumentID="{}" DocumentType="{}" DocumentName="{}" RelatedDocumentID="{}"/>\n'
        # The XML file is generated and validated in parts since the employer record and employee records are
        # delimiter separated and do not have a root tag and do not satisfy the XML standards.
        parent_delimiter = delimiter.format('1.1', 'PARENT', 'PAYEVNT', '').encode('utf-8')
        parent_report = self.env['ir.qweb']._render('l10n_au_hr_payroll_account.payevent_0004_xml_report', {'employer': employer, 'intermediary': intermediary, 'stp_id': self})
        parent_report, message = self._prettify_validate_xml(parent_report, 'l10n_au_payevnt_0004')
        report = parent_delimiter + parent_report

        for employee_index, employee in enumerate(employees):
            employee_delimiter = delimiter.format(f'1.{employee_index + 2}', 'CHILD', 'PAYEVNTEMP', '1.1').encode('utf-8')
            employee_report = self.env['ir.qweb']._render('l10n_au_hr_payroll_account.payeventemp_0004_xml_report', {'employee': employee})
            employee_report, error = self._prettify_validate_xml(employee_report, 'l10n_au_payevntemp_0004')
            report += employee_delimiter + employee_report
            message += error

        self.error_message = message
        self.xml_validation_state = "invalid" if message else "done"

        self.xml_file = base64.b64encode(report)

    def _check_stp_fields(self):
        self.ensure_one()
        if self.warning_message:
            raise ValidationError(self.warning_message)
        if not self.company_id.vat and not self.company_id.l10n_au_wpn_number:
            raise ValidationError(_("Please configure the WPN number or ABN in the company settings."))
        if self.company_id.vat and not self.company_id.l10n_au_branch_code:
            raise ValidationError(
                _("Please configure Branch code for %s. Branch code is required for ABN registered companies.", self.company_id.name)
            )

    def _check_payslips(self):
        self.ensure_one()
        if self.payslip_ids.filtered(lambda p: p.l10n_au_stp_status != 'ready'):
            raise ValidationError(_("Some payslips are not ready for STP submission!"))
        if self.payslip_batch_id and self.payslip_batch_id.l10n_au_stp_status != 'ready':
            raise ValidationError(_("The payslip batch is not ready for STP submission!"))

        # Employee fields check
        message = "Please configure the following fields for the employees:\n"
        faulty = False
        for emp in self.payslip_ids.employee_id:
            for field in EMPLOYEE_REQUIRED_FIELDS:
                if not emp[field]:
                    faulty = True
                    message += _("- %(field)s for Employee %(name)s.\n", field=emp._fields[field].string, name=emp.name)
        if faulty:
            raise ValidationError(message)

    def _finalise_records(self):
        self.ensure_one()
        self.l10n_au_stp_emp.payslip_ids.write({"l10n_au_finalised": True})
        self.l10n_au_stp_emp.ytd_balance_ids.write({"finalised": True})

    def submit(self):
        self.ensure_one()
        self.action_generate_xml()

        if not self.xml_file:
            raise ValidationError(_("The XML file could not be generated!"))

        self.state = 'sent'
        self.activity_feedback(
            ["l10n_au_hr_payroll_account.l10n_au_activity_submit_stp"],
            feedback=f"Submitted to ATO by {self.env.user.name}")

        if self.ffr:
            self.previous_report_id.message_post(
                body=_("A replacement file has been submitted for this report. Please check the new report. %s", (self._get_html_link())
            ))

    def action_replace_file(self):
        self.ensure_one()
        if self.ffr and (self.create_date - fields.Datetime.now()) < timedelta(hours=24):
            raise ValidationError(_("The replacement report has been submitted less than 24 hours ago. Please try again later."))

        if self.state != "sent" and not self.file_replacement_message:
            raise ValidationError(_("The report must be in the 'Submitted' state to replace the file. "
            "Please make any modifications before proceeding with submission."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Replace File"),
            "res_model": "l10n_au.stp.ffr.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_stp_id": self.id}
        }
