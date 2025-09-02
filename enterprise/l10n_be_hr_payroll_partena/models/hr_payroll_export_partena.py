# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from math import ceil

from odoo import api, models, fields, _
from odoo.exceptions import UserError

MINIUTES_PER_DAY = 8 * 60


class L10nBeHrPayrollExportPartena(models.Model):
    _inherit = 'hr.work.entry.export.mixin'
    _name = 'l10n.be.hr.payroll.export.partena'
    _description = 'Export Payroll to Partena'

    eligible_employee_line_ids = fields.One2many('l10n.be.hr.payroll.export.partena.employee')

    @api.model
    def _country_restriction(self):
        return 'BE'

    def _generate_header(self):
        return (
            'DOSSIER;NRWORKER;DAYDATE;PRESTATYPE;CODE;MINUTES_DAY;SIGNAL_A;'
            'SIGNAL_B;SIGNAL_AMOUNT;PAY_A;PAY_B;PAY_AMOUNT;DEPT;TREATMENT;'
            'SALARYAMOUNT;SALARYPERC;B_PRINCIPAL;CODECLOCK;CLOCK_AMOUNT;'
            'REPLACE_VALUE;THEOHOURS;SALARYUNIT;HOURRATE;SHIFTCODE;SHIFTUNIT;'
            'SHIFTAMOUNT;SHIFTHOST;THEODEPT;COMPLETED;FILLER1;FILLER2;FILLER3;'
            'FILLER4;FILLER5;FILLER6;FILLER7;MEMO\n'
        )

    def _generate_line(self, employee, date, work_entry_collection=None):
        """
        Generate a line for the export file.
        """
        if work_entry_collection is None:
            partena_code = '---  '
            duration = MINIUTES_PER_DAY
        else:
            partena_code = work_entry_collection.work_entries[0].work_entry_type_id.partena_code
            duration = ceil(work_entry_collection.duration / 60)  # in minutes
        return '%(pc_company)s;%(pc_employee)s;%(date)s;D;%(pc_we)s;%(duration)s' % {
            'pc_company': self.env.company.partena_code,
            'pc_employee': employee.partena_code,
            'date': date.strftime('%Y%m%d'),
            'pc_we': partena_code,
            'duration': duration,
        } + ';;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;' + '\n'

    def _generate_export_file(self):
        self.ensure_one()
        names = [
            employee.name for employee in self.eligible_employee_line_ids.employee_id
            if not employee.partena_code]
        if names:
            raise UserError(_(
                'The following employees do not have a Partena code: %(names)s',
                names=', '.join(names)))
        file = self._generate_header()
        days_in_period = (self.period_stop - self.period_start).days + 1
        for employee_line in self.eligible_employee_line_ids:
            we_by_day_and_code = employee_line._get_work_entries_by_day_and_code()
            for date in (self.period_start + timedelta(days=offset) for offset in range(days_in_period)):
                if we_by_code := we_by_day_and_code.get(date):
                    for work_entry_collection in we_by_code.values():
                        file += self._generate_line(employee_line.employee_id, date, work_entry_collection)
                else:
                    file += self._generate_line(employee_line.employee_id, date)
        return file

    def _generate_export_filename(self):
        return 'CLOCK_ODOO_%(pc_company)s_%(company_id)06d_%(datetime)s.csv' % {
            'pc_company': self.env.company.partena_code,
            'company_id': self.env.company.id,
            'datetime': datetime.now().strftime('%Y%m%d%H%M%S'),
        }

    def _get_name(self):
        return _('Export to Partena')


class L10nBeHrPayrollExportPartenaEmployee(models.Model):
    _name = 'l10n.be.hr.payroll.export.partena.employee'
    _description = 'Partena Export Employee'
    _inherit = 'hr.work.entry.export.employee.mixin'

    export_id = fields.Many2one('l10n.be.hr.payroll.export.partena')
