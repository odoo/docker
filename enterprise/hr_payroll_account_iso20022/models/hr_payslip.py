# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    iso20022_uetr = fields.Char(
        string='UETR',
        help='Unique end-to-end transaction reference',
    )

    def _get_payments_vals(self, journal_id):
        self.ensure_one()

        payment_vals = {
            'id': self.id,
            'name': self.number,
            'payment_date': fields.Date.today(),
            'amount': self.net_wage,
            'journal_id': journal_id.id,
            'currency_id': journal_id.currency_id.id,
            'payment_type': 'outbound',
            'memo': self.number,
            'partner_id': self.employee_id.work_contact_id.id,
            'partner_bank_id': self.employee_id.bank_account_id.id,
        }
        if journal_id.sepa_pain_version == 'pain.001.001.09':
            if not self.iso20022_uetr:
                payment_vals['iso20022_uetr'] = self.iso20022_uetr = str(uuid4())
            else:
                payment_vals['iso20022_uetr'] = self.iso20022_uetr

        return payment_vals

    def action_payslip_payment_report(self, export_format='sepa'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.payment.report.wizard',
            'view_mode': 'form',
            'view_id': 'hr_payslip_payment_report_view_form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_payslip_ids': self.ids,
                'default_payslip_run_id': self.payslip_run_id.id,
                'default_export_format': export_format,
            },
        }
