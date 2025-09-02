from odoo import models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_payment_report(self, export_format='sepa'):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.payment.report.wizard',
            'view_mode': 'form',
            'view_id': 'hr_payslip_payment_report_view_form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_payslip_ids': self.slip_ids.ids,
                'default_payslip_run_id': self.id,
                'default_export_format': export_format,
            },
        }
