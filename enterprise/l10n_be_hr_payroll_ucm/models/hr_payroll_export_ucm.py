# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class L10nBeHrPayrollExportUCM(models.Model):
    _inherit = 'hr.work.entry.export.mixin'
    _name = 'l10n.be.hr.payroll.export.ucm'
    _description = 'Export Payroll to UCM'

    eligible_employee_line_ids = fields.One2many('l10n.be.hr.payroll.export.ucm.employee')

    @api.model
    def _country_restriction(self):
        return 'BE'

    def _generate_line(self, employee, date, work_entry_collection):
        """
        Generate a line for the export file.
        """
        ucm_code = work_entry_collection.work_entries[0].work_entry_type_id.ucm_code
        if not ucm_code:
            raise UserError(_(
                'The work entry type %(we)s does not have a UCM code',
                we=work_entry_collection.work_entries[0].work_entry_type_id
            ))
        hours = f'{int(work_entry_collection.duration // 3600):02d}'
        hundredth_of_hours = f'{int((work_entry_collection.duration % 3600) // 36):02d}'
        return self.company_id.ucm_company_code + f'{employee.ucm_code:0>5}' \
            + date.strftime('%m%Y%d') + ucm_code + hours + hundredth_of_hours \
            + '0000000             ' + '\n'

    def _generate_export_file(self):
        self.ensure_one()
        names = [
            employee.name for employee in self.eligible_employee_line_ids.employee_id
            if not employee.ucm_code]
        if names:
            raise UserError(_(
                'The following employees do not have a ucm code: %(names)s',
                names=', '.join(names)))
        file = ''
        for employee_line in self.eligible_employee_line_ids:
            we_by_day_and_code = employee_line._get_work_entries_by_day_and_code()
            for date, we_by_code in we_by_day_and_code.items():
                for work_entry_collection in we_by_code.values():
                    file += self._generate_line(employee_line.employee_id, date, work_entry_collection)
        return file

    def _generate_export_filename(self):
        return '%(ucm_company)s_RP_%(reference_time)s_%(datetime)s.txt' % {
            'ucm_company': self.env.company.ucm_code,
            'reference_time': self.period_start.strftime('%Y%m'),
            'datetime': datetime.now().strftime('%Y%m%d_%H%M%S'),
        }

    def _get_name(self):
        return _('Export to UCM')


class L10nBeHrPayrollExportUCMEmployee(models.Model):
    _name = 'l10n.be.hr.payroll.export.ucm.employee'
    _description = 'UCM Export Employee'
    _inherit = 'hr.work.entry.export.employee.mixin'

    export_id = fields.Many2one('l10n.be.hr.payroll.export.ucm')
