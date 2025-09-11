# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, models


class payroll_advice_report(models.AbstractModel):
    _name = 'report.l10n_in_hr_payroll.report_payrolladvice'
    _description = "Indian Payroll Advice Report"

    def get_month(self, input_date):
        res = {
               'from_name': '', 'to_name': ''
               }
        slip = self.env['hr.payslip'].search([('date_from', '<=', input_date), ('date_to', '>=', input_date)], limit=1)
        if slip:
            from_date = slip.date_from
            to_date = slip.date_to
            res['from_name'] = from_date.strftime('%d') + '-' + from_date.strftime('%B') + '-' + from_date.strftime('%Y')
            res['to_name'] = to_date.strftime('%d') + '-' + to_date.strftime('%B') + '-' + to_date.strftime('%Y')
        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        payment_report = self.env['hr.payroll.payment.report.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'hr.payroll.payment.report.wizard',
            'data': data,
            'docs': payment_report,
            'time': time,
            'get_month': self.get_month,
        }
