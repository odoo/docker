# -*- coding: utf-8 -*-
import base64

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInvoices(AccountTestInvoicingCommon):

    def test_suspense_statement_line_id(self):
        reconcile_activity_type = self.env['mail.activity.type'].create({
            "name": "Reconciliation request",
            "category": "upload_file",
            "folder_id": self.env.ref("documents.document_finance_folder").id,
            "res_model": "account.move",
            "tag_ids": [(6, 0, [self.env.ref('documents.documents_tag_to_validate').id])],
        })

        st = self.env['account.bank.statement'].create({
            'line_ids': [Command.create({
                'amount': -1000.0,
                'date': '2017-01-01',
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_ref': 'test_suspense_statement_line_id',
            })],
        })
        st.balance_end_real = st.balance_end
        st_line = st.line_ids
        move = st_line.move_id

        # Log an activity on the move using the "Reconciliation Request".
        activity = self.env['mail.activity'].create({
            'activity_type_id': reconcile_activity_type.id,
            'note': "test_suspense_statement_line_id",
            'res_id': move.id,
            'res_model_id': self.env.ref('account.model_account_move').id,
        })
        activity._onchange_activity_type_id()

        # A new document has been created.
        documents = self.env['documents.document'].search([('request_activity_id', '=', activity.id)])
        self.assertTrue(documents.exists())

        # Upload an attachment.
        attachment = self.env['ir.attachment'].create({
            'name': "test_suspense_statement_line_id",
            'datas': base64.b64encode(bytes("test_suspense_statement_line_id", 'utf-8')),
            'res_model': move._name,
            'res_id': move.id,
        })
        activity._action_done(attachment_ids=attachment.ids)

        # Upload as a vendor bill.
        vendor_bill_action = documents.account_create_account_move('in_invoice')
        self.assertTrue(vendor_bill_action.get('res_id'))
        vendor_bill = self.env['account.move'].browse(vendor_bill_action['res_id'])

        self.assertRecordValues(vendor_bill, [{'suspense_statement_line_id': st_line.id}])

        folder_test = self.env['documents.document'].create({'name': 'Test Bills','type':'folder'})
        self.env.user.company_id.documents_account_settings = True

        invoice = self.init_invoice("in_invoice", amounts=[1000], post=True)
        setting = self.env['documents.account.folder.setting'].create({
            'folder_id': folder_test.id,
            'journal_id': invoice.journal_id.id,
        })

        test_partner = self.env['res.partner'].create({'name':'test Azure'})
        document = self.env['documents.document'].create({
            'datas': base64.b64encode(bytes("test_suspense_statement_line_id", 'utf-8')),
            'name': 'file.txt',
            'mimetype': 'text/plain',
            'partner_id':test_partner.id,
        })

        document.account_create_account_move('in_invoice')

        self.assertTrue(document.partner_id.id,test_partner.id)
