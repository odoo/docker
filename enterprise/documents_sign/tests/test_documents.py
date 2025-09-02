# -*- coding: utf-8 -*-

import base64
from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tools import file_open, mute_logger
from odoo.addons.sign.tests.sign_request_common import SignRequestCommon

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


class TestCaseDocumentsBridgeSign(SignRequestCommon):
    """

    """
    def setUp(self):
        super(TestCaseDocumentsBridgeSign, self).setUp()

        with file_open('sign/static/demo/sample_contract.pdf', "rb") as f:
            pdf_content = f.read()

        self.folder_a = self.env['documents.document'].create({
            'name': 'folder A',
            'type': 'folder',
        })
        self.folder_a_a = self.env['documents.document'].create({
            'name': 'folder A - A',
            'type': 'folder',
            'folder_id': self.folder_a.id,
        })
        self.documents = self.env['documents.document'].create([{
            'datas': base64.encodebytes(pdf_content),
            'name': f'file_{idx}.pdf',
            'folder_id': self.folder_a_a.id,
        } for idx in range(2)])
        self.document_pdf_0 = self.documents[0]

    def test_bridge_folder_workflow(self):
        """
        tests the create new business model (sign).
    
        """
        self.assertEqual(self.document_pdf_0.res_model, 'documents.document', "failed at default res model")
        self.documents.document_sign_create_sign_template_x('sign.template.new', self.folder_a.id)

        with self.assertRaises(UserError, msg="Can only be executed on one record."):
            self.documents.document_sign_create_sign_template_x('sign.template.direct', self.folder_a.id)
    
        self.assertEqual(self.document_pdf_0.res_model, 'sign.template',
                         "failed at workflow_bridge_dms_sign new res_model")
        template = self.env['sign.template'].search([('id', '=', self.document_pdf_0.res_id)])
        self.assertTrue(template.exists(), 'failed at workflow_bridge_dms_account template')
        self.assertEqual(self.document_pdf_0.res_id, template.id, "failed at workflow_bridge_dms_account res_id")

    @mute_logger('odoo.addons.documents.models.documents_document')
    def test_sign_action(self):
        """ Test sign a document from Document app using the workflow rule. """
        self.document_pdf_0.document_sign_create_sign_template_x('sign.template.direct', self.folder_a.id)
        self.assertEqual(self.document_pdf_0.res_model, 'sign.template')
        template = self.env['sign.template'].search([('id', '=', self.document_pdf_0.res_id)])
        # Get the sign item for the customer from template_3_roles and assign it to the template
        self.template_3_roles.sign_item_ids[0].copy().template_id = template
        sign_request = self.env['sign.request'].create({
            'template_id': template.id,
            'reference': template.display_name,
            'request_item_ids': [Command.create({
                'partner_id': self.partner_1.id,
                'role_id': self.env.ref('sign.sign_item_role_customer').id,
            })],
        })
        sign_request_item = sign_request.request_item_ids[0]
        sign_values = self.create_sign_values(template.sign_item_ids, self.role_customer.id)

        sign_request_item._edit_and_sign(sign_values)
        self.assertEqual(sign_request_item.state, 'completed', 'The sign.request.item should be completed')

    @mute_logger("odoo.addons.documents.models.documents_document")  # avoid warning about counting page of PDFs
    def test_signed_documents_access_rights(self):
        """ Test access rights and owner of signed/certificate documents. """
        Document = self.env["documents.document"]
        Partner = self.env["res.partner"]
        User = self.env["res.users"]
        user_root = self.env.ref("base.user_root")

        users = User.create([
            {
                "name": f"test_sign_owner_{group}",
                "login": f"test_sign_owner_{group}@ex.com",
                "email": f"test_sign_owner_{group}@ex.com",
                "groups_id": [Command.set([self.env.ref(group).id])]
            } for group in ("base.group_portal", "base.group_user", "sign.group_sign_user", "sign.group_sign_manager")
        ])
        user_sign_manager = users[-1]
        self.template_1_role.folder_id = self.folder_a
        self.folder_a.action_update_access_rights(partners={user_sign_manager.partner_id: ('edit', False)})

        all_documents_signed = self.env['documents.document']
        for user in users:
            with self.subTest(user_name=user.name):
                sign_request = self.create_sign_request_1_role(user.partner_id, Partner)
                # See /sign/sign/<int:sign_request_id>/<token> controller
                sign_request.request_item_ids[0].with_user(user).sudo()._edit_and_sign(
                    {str(self.template_1_role.sign_item_ids[0].id): "Test Sign"})
                self.env['documents.access'].invalidate_model()
                documents_signed = Document.search(
                    [('res_model', '=', 'sign.request'), ('res_id', '=', sign_request.id)])
                all_documents_signed |= documents_signed
                self.assertEqual(len(documents_signed), 2)
                self.assertEqual(documents_signed.owner_id, self.env.ref('base.user_root'),
                                 "Owner of the signed/certificate documents must be odooBot.")
                # The signed documents inherits from the folder access rights -> cannot access the signed documents
                for doc in documents_signed:
                    self.assertEqual(doc.access_via_link, "none")
                    self.assertEqual(doc.access_internal, "none")
                    self.assertTrue(doc.is_access_via_link_hidden)
                    self.assertEqual(doc.owner_id, user_root)
                    self.assertEqual(doc.partner_id, user.partner_id)
                    access_by_partner = {access.partner_id: access for access in doc.access_ids}
                    self.assertEqual(len(doc.access_ids), 1 if user == user_sign_manager else 2)
                    access_manager = access_by_partner.get(user_sign_manager.partner_id)
                    self.assertTrue(access_manager)
                    self.assertEqual(access_manager.role, "edit")
                    self.assertFalse(access_manager.expiration_date)
                    if user != user_sign_manager:
                        access_signer = access_by_partner.get(user.partner_id)
                        self.assertTrue(access_signer)
                        self.assertEqual(access_signer.role, "view")
                        self.assertFalse(access_signer.expiration_date)
                    if user == user_sign_manager:
                        break
                    doc.with_user(user).mapped("name")
                    with self.assertRaises(
                            AccessError,
                            msg="Users without edit permission on the folder cannot edit the signature",
                    ):
                        doc.with_user(user).write({"name": "New name"})

        # user_sign_manager have edit access on all the signed documents
        self.assertEqual(len(all_documents_signed), 8)
        for doc in all_documents_signed:
            doc.with_user(user_sign_manager).name = "Name overridden by the manager"
