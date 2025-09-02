# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    nacha_effective_date = fields.Date('The effective date of the NACHA file generated for this payslip')

    def action_payslip_payment_report(self, export_format='nacha'):
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
                'default_export_format': export_format,
            },
        }
