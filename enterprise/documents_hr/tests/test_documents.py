# -*- coding: utf-8 -*-

from odoo import http
from odoo.tests.common import HttpCase, RecordCapturer, tagged

from .test_documents_hr_common import TransactionCaseDocumentsHr


@tagged('post_install', '-at_install', 'test_document_bridge')
class TestCaseDocumentsBridgeHR(HttpCase, TransactionCaseDocumentsHr):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employee (related to doc_user)',
            'user_id': cls.doc_user.id,
            'work_contact_id': cls.doc_user.partner_id.id
        })

    def test_bridge_hr_settings_on_write(self):
        """
        Makes sure the settings apply their values when an ir_attachment is set as message_main_attachment_id
        on invoices.
        """
        attachment_txt_test = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'hr.employee',
            'res_id': self.employee.id,
        })

        document = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
        self.assertTrue(document.exists(), "There should be a new document created from the attachment")
        self.assertEqual(document.owner_id, self.user_root, "The owner_id should be odooBot")
        self.assertEqual(document.partner_id, self.employee.work_contact_id, "The partner_id should be the employee's address")
        self.assertEqual(document.access_via_link, "none")
        self.assertEqual(document.access_internal, "none")
        self.assertTrue(document.is_access_via_link_hidden)

    def test_upload_employee_attachment(self):
        """
        Make sure an employee's attachment is linked to the existing document
        and a new one is not created.
        """
        document = self.env['documents.document'].create({
            'name': 'Doc',
            'folder_id': self.hr_folder.id,
            'res_model': self.employee._name,
            'res_id': self.employee.id,
        })
        document.write({
            'datas': self.TEXT,
            'mimetype': 'text/plain',
        })
        self.assertTrue(document.attachment_id, "An attachment should have been created")

    def test_hr_employee_document_auto_created_not_shared_with_employee(self):
        """ Test that automatically created employee documents from attachment are not shared with the employee. """
        attachment = self.env['ir.attachment'].create({
            'name': 'test.txt',
            'mimetype': 'text/plain',
            'datas': self.TEXT,
            'res_model': 'hr.employee',
            'res_id': self.employee.id,
        })
        document = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])
        self.assertTrue(document)
        self.assertEqual(document.with_user(self.employee.user_id).user_permission, 'none')

    def test_hr_employee_document_upload_not_shared_with_employee(self):
        """Test that uploaded hr.employee documents are not shared with the employee."""
        self.authenticate(self.hr_manager.login, self.hr_manager.login)
        with RecordCapturer(self.env['documents.document'], []) as capture:
            res = self.url_open(f'/documents/upload/{self.hr_folder.access_token}',
                data={
                    'csrf_token': http.Request.csrf_token(self),
                    'res_id': self.employee.id,
                    'res_model': 'hr.employee',
                },
                files={'ufile': ('hello.txt', b"Hello", 'text/plain')},
            )
            res.raise_for_status()
        document = capture.records.ensure_one()
        self.assertEqual(document.res_model, "hr.employee",
                         "The uploaded document is linked to the employee model")
        self.assertEqual(document.res_id, self.employee.id,
                         "The uploaded document is linked to the employee record")
        self.assertEqual(document.with_user(self.doc_user).user_permission, "none",
                         "The employee has no access to the uploaded document")
        self.assertEqual(document.with_user(self.hr_manager).user_permission, "edit",
                         "The HR manager has access to the uploaded document")

    def test_open_document_from_hr(self):
        """ Test that opening the document app from an employee (hr app) is opening it in the right context. """
        action = self.employee.action_open_documents()
        context = action['context']
        self.assertTrue(context['searchpanel_default_folder_id'])
        self.assertEqual(context['default_res_model'], 'hr.employee')
        self.assertEqual(context['default_res_id'], self.employee.id)
        self.assertEqual(context['default_partner_id'], self.employee.work_contact_id.id)
        employee_related_doc, *__ = self.env['documents.document'].create([
            {'name': 'employee doc', 'partner_id': self.employee.work_contact_id.id},
            {'name': 'employee doc 2', 'owner_id': self.employee.user_id.id},
            {'name': 'non employee'},
        ])
        filtered_documents = self.env['documents.document'].search(action['domain']).filtered(lambda d: d.type != 'folder')
        self.assertEqual(
            len(filtered_documents.filtered(
                lambda doc: doc.owner_id == self.employee.user_id or doc.partner_id == self.employee.work_contact_id)),
            1,
            "Employee related document is visible")
        self.assertEqual(filtered_documents, employee_related_doc, "Only employee-related document is visible")
