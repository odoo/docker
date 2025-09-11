# -*- coding: utf-8 -*-

from odoo.addons.documents_hr.tests.test_documents_hr_common import TransactionCaseDocumentsHr
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestCaseDocumentsBridgeRecruitment(TransactionCaseDocumentsHr):

    @classmethod
    def setUpClass(cls):
        super(TestCaseDocumentsBridgeRecruitment, cls).setUpClass()
        cls.folder = cls.env['documents.document'].create({'name': 'folder_test', 'type': 'folder'})
        cls.company = cls.env['res.company'].create({
            'name': 'test bridge recruitment',
            'recruitment_folder_id': cls.folder.id,
            'documents_recruitment_settings': True,
        })

    def test_job_attachment(self):
        """
        Document is created from job attachment
        """
        job = self.env['hr.job'].create({
            'name': 'Cobble Dev :/',
            'company_id': self.company.id
        })
        attachment = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': job._name,
            'res_id': job.id
        })

        doc = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])

        self.assertTrue(doc, "It should have created a document")
        self.assertEqual(doc.folder_id, self.folder, "It should be in the correct folder")
        self.assertEqual(doc.owner_id, self.env.ref('base.user_root'), "The owner_id should be odooBot")
        self.assertEqual(doc.access_via_link, "none")
        self.assertEqual(doc.access_internal, "none")
        self.assertTrue(doc.is_access_via_link_hidden)
        self.check_document_no_access(doc, self.doc_user_2)
        self.check_document_no_access(doc, self.document_manager)

    def test_applicant_attachment(self):
        """
        Document is created from applicant attachment
        """
        partner = self.env['res.partner'].create({
            'name': 'Applicant Partner',
        })
        applicant = self.env['hr.applicant'].create({
            'candidate_id': self.env['hr.candidate'].create({'partner_id': partner.id, 'company_id': self.company.id}).id,
            'company_id': self.company.id,
        })
        attachment = self.env['ir.attachment'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
            'res_model': applicant._name,
            'res_id': applicant.id,
        })

        doc = self.env['documents.document'].search([('attachment_id', '=', attachment.id)])

        self.assertTrue(doc, "It should have created a document")
        self.assertEqual(doc.folder_id, self.folder, "It should be in the correct folder")
        self.assertEqual(doc.partner_id, partner, "The partner_id should be the applicant's partner_id")
        self.assertEqual(doc.owner_id, self.env.ref('base.user_root'), "The owner_id should be odooBot")
        self.assertEqual(doc.access_via_link, "none")
        self.assertEqual(doc.access_internal, "none")
        self.assertTrue(doc.is_access_via_link_hidden)
        self.check_document_no_access(doc, self.doc_user_2)
        self.check_document_no_access(doc, self.document_manager)

    def test_create_applicant_action(self):
        document = self.env['documents.document'].create({
            'datas': self.TEXT,
            'name': 'fileTextTwo.txt',
            'mimetype': 'text/plain',
        })
        action = document.document_hr_recruitment_create_hr_candidate()
        self.assertEqual(document.res_model, 'hr.candidate', "The document is linked to the created candidate.")
        applicant = self.env['hr.candidate'].search([('id', '=', document.res_id)])
        self.assertTrue(applicant.exists(), 'Candidate has been created.')
        self.assertTrue(action)
