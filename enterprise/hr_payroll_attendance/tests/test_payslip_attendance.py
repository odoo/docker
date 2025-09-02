# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_work_entry_contract_attendance.tests.common import HrWorkEntryAttendanceCommon

from datetime import datetime, date

from odoo.tests import tagged

@tagged('-at_install', 'post_install')
class TestPayslipAttendance(HrWorkEntryAttendanceCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.struct_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Test Structure Type',
            'wage_type': 'hourly',
        })
        cls.struct = cls.env['hr.payroll.structure'].create({
            'name': 'Test Structure - Worker',
            'type_id': cls.struct_type.id,
        })
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Test Payslip',
            'employee_id': cls.employee.id,
            'struct_id': cls.struct.id,
            'date_from': '2024-1-1',
            'date_to': '2024-1-30',
        })

    def test_get_attendance_from_payslip(self):
        attendance_A, attendance_B, *_ = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 1, 8, 0, 0),
                'check_out': datetime(2024, 1, 1, 16, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 20, 8, 0, 0),
                'check_out': datetime(2024, 1, 20, 16, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 2, 1, 8, 0, 0),
                'check_out': datetime(2024, 2, 1, 16, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 2, 20, 8, 0, 0),
                'check_out': datetime(2024, 2, 20, 16, 0, 0),
            },
        ])
        attendance_by_payslip = self.payslip._get_attendance_by_payslip()
        self.assertEqual(attendance_by_payslip[self.payslip], attendance_A + attendance_B)

    def test_get_attendance_from_payslip_with_timezone(self):
        attendance_A, attendance_B, = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 1, 7, 0, 0),
                'check_out': datetime(2024, 1, 1, 15, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2024, 1, 30, 23, 30, 0), # 2024-1-31 00-30-00 in UTC+1
                'check_out': datetime(2024, 1, 31, 7, 30, 0),
            },
        ])

        # Without using `_get_attendance_by_payslip`
        domain = [
            ('employee_id', '=', self.employee.id),
            ('check_in', '<=', self.payslip.date_to),
            ('check_out', '>=', self.payslip.date_from)
        ]
        attendances = self.env['hr.attendance'].with_context(tz="Europe/Brussels").search(domain)
        self.assertEqual(attendances, attendance_A + attendance_B) # Not correct (`attendance_B` is not in the payslip period)
        # With using `_get_attendance_by_payslip`:
        attendance_by_payslip = self.payslip.with_context(tz="Europe/Brussels")._get_attendance_by_payslip()
        self.assertEqual(attendance_by_payslip[self.payslip], attendance_A) # Correct

    def test_compute_payslip_no_worked_hours(self):
        employee = self.env['hr.employee'].create({'name': 'John'})
        contract = self.env['hr.contract'].create({
            'name': 'Contract for John',
            'wage': 5000,
            'employee_id': employee.id,
            'date_start': date(2024, 10, 1),
            'date_end': date(2024, 10, 31),
            'work_entry_source': 'attendance',
            'structure_type_id': self.struct_type.id,
            'state': 'open',
        })

        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of John',
            'employee_id': employee.id,
            'contract_id': contract.id,
            'struct_id': self.struct.id,
            'date_from': date(2024, 10, 1),
            'date_to': date(2024, 10, 31)
        })

        payslip.compute_sheet()
        basic_salary_line = payslip.line_ids.filtered_domain([('code', '=', 'BASIC')])
        self.assertAlmostEqual(basic_salary_line.amount, 0.0, 2, 'Basic salary = 0 worked hours * hourly wage = 0')
