# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    l10n_sa_wps_file_reference = fields.Char(string="WPS File Reference", copy=False)

    _sql_constraints = [
        ('l10n_sa_wps_unique_reference', 'UNIQUE(l10n_sa_wps_file_reference)',
         'WPS File reference must be unique'),
    ]

    def _l10n_sa_wps_generate_file_reference(self):
        self.ensure_one()
        if not self.l10n_sa_wps_file_reference:
            # Required unique 16 character reference
            self.l10n_sa_wps_file_reference = self.env['ir.sequence'].next_by_code("l10n_sa.wps")
            self.slip_ids.l10n_sa_wps_file_reference = self.l10n_sa_wps_file_reference
        return self.l10n_sa_wps_file_reference

    def action_payment_report(self, export_format='l10n_sa_wps'):
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
