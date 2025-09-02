# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from dateutil.relativedelta import relativedelta


class TestPayslipFlow(TestPayslipBase):

    def test_00_payslip_flow(self):
        """ Testing payslip flow and report printing """
        # activate Richard's contract
        self.richard_emp.contract_ids[0].state = 'open'

        # I create an employee Payslip
        richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id
        })

        payslip_input = self.env['hr.payslip.input'].search([('payslip_id', '=', richard_payslip.id)])
        # I assign the amount to Input data
        payslip_input.write({'amount': 5.0})

        # I verify the payslip is in draft state
        self.assertEqual(richard_payslip.state, 'draft', 'State not changed!')

        richard_payslip.compute_sheet()

        # Then I click on the 'Confirm' button on payslip
        richard_payslip.action_payslip_done()

        # I verify that the payslip is in done state
        self.assertEqual(richard_payslip.state, 'done', 'State not changed!')

        # Then I click on the 'Mark as paid' button on payslip
        richard_payslip.action_payslip_paid()

        # I verify that the payslip is in paid state
        self.assertEqual(richard_payslip.state, 'paid', 'State not changed!')

        # I want to check refund payslip so I click on refund button.
        richard_payslip.refund_sheet()

        # I check on new payslip Credit Note is checked or not.
        payslip_refund = self.env['hr.payslip'].search([('name', 'like', 'Refund: '+ richard_payslip.name), ('credit_note', '=', True)])
        self.assertTrue(bool(payslip_refund), "Payslip not refunded!")

        # I want to generate a payslip from Payslip run.
        payslip_run = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })

        # I create record for generating the payslip for this Payslip run.

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id)]
        })

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

    def test_01_batch_with_specific_structure(self):
        """ Generate payslips for the employee whose running contract is based on the same Salary Structure Type"""

        specific_structure_type = self.env['hr.payroll.structure.type'].create({
            'name': 'Structure Type Test'
        })

        specific_structure = self.env['hr.payroll.structure'].create({
            'name': 'End of the Year Bonus - Test',
            'type_id': specific_structure_type.id,
        })

        self.richard_emp.contract_ids[0].state = 'open'

        # 13th month pay
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'End of the year bonus'
        })
        # I create record for generating the payslip for this Payslip run.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'structure_id': specific_structure.id,
        })

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id)._compute_employee_ids()

        self.assertFalse(payslip_employee.employee_ids)

        # Update the structure type and generate payslips again
        specific_structure_type.default_struct_id = specific_structure.id
        self.richard_emp.contract_ids[0].structure_type_id = specific_structure_type.id

        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'Batch for Structure'
        })

        payslip_employee = self.env['hr.payslip.employees'].create({
            'structure_id': specific_structure.id,
        })

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id)._compute_employee_ids()

        self.assertTrue(payslip_employee.employee_ids)
        self.assertTrue(self.richard_emp.id in payslip_employee.employee_ids.ids)

        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

        self.assertEqual(len(payslip_run.slip_ids), 1)
        self.assertEqual(payslip_run.slip_ids.struct_id.id, specific_structure.id)

    def test_02_payslip_batch_with_archived_employee(self):
        # activate Richard's contract
        self.richard_emp.contract_ids[0].state = 'open'
        # archive his contact
        self.richard_emp.action_archive()

        # 13th month pay
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'End of the year bonus'
        })
        # I create record for generating the payslip for this Payslip run.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id)],
        })
        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

        self.assertEqual(len(payslip_run.slip_ids), 1)

    def test_03_payslip_batch_with_payment_process(self):
        '''
            Test to check if some payslips in the batch are already paid,
            the batch status can be updated to 'paid' without affecting
            those already paid payslips.
        '''

        self.richard_emp.contract_ids[0].state = 'open'
        self.contract_jules = self.env['hr.contract'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'name': 'Contract for Jules',
            'wage': 5000.33,
            'employee_id': self.jules_emp.id,
            'state': 'open',
        })

        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'Payment Test'
        })

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id), (4, self.jules_emp.id)],
        })

        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.action_validate()

        self.assertEqual(len(payslip_run.slip_ids), 2)
        self.assertTrue(all(payslip.state == 'done' for payslip in payslip_run.slip_ids), 'State not changed!')

        # Mark the first payslip as paid and store the paid date
        payslip_run.slip_ids[0].action_payslip_paid()
        paid_date = payslip_run.slip_ids[0].paid_date

        self.assertEqual(payslip_run.slip_ids[0].state, 'paid', 'State not changed!')
        self.assertEqual(payslip_run.slip_ids[1].state, 'done', 'State not changed!')

        payslip_run.action_paid()

        self.assertEqual(payslip_run.state, 'paid', 'State not changed!')
        self.assertTrue(all(payslip.state == 'paid' for payslip in payslip_run.slip_ids), 'State not changed!')
        self.assertEqual(payslip_run.slip_ids[0].paid_date, paid_date, 'payslip paid date should not be changed')
