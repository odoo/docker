# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.documents_hr.tests.test_documents_hr_common import TransactionCaseDocumentsHr
from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.tests.common import tagged


@tagged('test_document_bridge')
class TestCaseDocumentsBridgeHR(TestPayslipBase, TransactionCaseDocumentsHr):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payroll_manager = cls.env['res.users'].create({
            'name': "Hr payroll manager test",
            'login': "hr_payroll_manager_test",
            'email': "hr_payroll_manager_test@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('hr_payroll.group_hr_payroll_user').id])]
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employee (related to doc_user_2)',
            'user_id': cls.doc_user_2.id,
            'work_contact_id': cls.doc_user_2.partner_id.id
        })
        cls.payroll_folder = cls.env['documents.document'].create({
            'name': 'Payroll',
            'type': 'folder',
            'access_internal': 'view',
        })
        cls.payroll_folder.action_update_access_rights(partners={cls.payroll_manager.partner_id: ('edit', False)})
        cls.env.user.company_id.documents_payroll_folder_id = cls.payroll_folder.id
        cls.richard_emp.work_contact_id = cls.doc_user.partner_id
        cls.richard_emp.user_id = cls.doc_user
        cls.contract = cls.richard_emp.contract_ids[0]
        cls.contract.state = 'open'
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': cls.richard_emp.id,
            'contract_id': cls.contract.id,
        })

    def test_payslip_document_creation(self):
        self.payslip.compute_sheet()
        self.payslip.with_context(payslip_generate_pdf=True, payslip_generate_pdf_direct=True).action_payslip_done()

        attachment = self.env['ir.attachment'].search([('res_model', '=', self.payslip._name), ('res_id', '=', self.payslip.id)])
        self.assertTrue(attachment, "Validating a payslip should have created an attachment")

        document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
        self.assertTrue(document, "There should be a new document created from the attachment")
        self.assertEqual(document.owner_id, self.env.ref('base.user_root'), "The owner_id should be odooBot")
        self.assertEqual(document.partner_id, self.richard_emp.work_contact_id, "The partner_id should be the employee's address")
        self.assertEqual(document.folder_id, self.payroll_folder, "The document should have been created in the configured folder")
        self.assertEqual(document.access_via_link, "none")
        self.assertEqual(document.access_internal, "none")
        self.assertTrue(document.is_access_via_link_hidden)
        self.check_document_no_access(document, self.doc_user_2)
        self.check_document_no_access(document, self.document_manager)

    def test_hr_payslip_document_creation_permission_employee_only(self):
        """ created hr.payslip documents are only viewable by the employee and editable by payroll managers. """
        self.check_document_creation_permission(self.payslip, self.payroll_folder, self.payroll_manager)
