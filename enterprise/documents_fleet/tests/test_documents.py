# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.exceptions import AccessError
from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase

TEXT = base64.b64encode(bytes("documents_fleet", 'utf-8'))


@tagged('post_install', '-at_install', 'test_document_bridge')
class TestCaseDocumentsBridgeFleet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fleet_folder = cls.env.ref('documents_fleet.document_fleet_folder')
        company = cls.env.user.company_id
        company.documents_fleet_settings = True
        company.documents_fleet_folder = cls.fleet_folder
        cls.manager_1 = new_test_user(cls.env, "test fleet manager",
            groups="documents.group_documents_user, fleet.fleet_group_manager"
        )
        cls.manager_2 = new_test_user(cls.env, "test fleet manager 2",
            groups="fleet.fleet_group_manager"
        )
        cls.user = new_test_user(cls.env, "user")
        # Create the Audi vehicle
        brand = cls.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = cls.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        cls.fleet_vehicle = cls.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": cls.manager_1.partner_id.id,
            "plan_to_change_car": False
        })

    def test_fleet_attachment(self):
        """
        Make sure the vehicle attachment is linked to the documents application

        Test Case:
        =========
            - Attach attachment to Audi vehicle
            - Check if the document is created
            - Check the res_id of the document
            - Check the res_model of the document
        """
        self.fleet_folder.access_ids.unlink()
        self.env['documents.access'].create([
            {'document_id': self.fleet_folder.id, 'partner_id': self.manager_1.partner_id.id, 'role': 'edit'},
            {'document_id': self.fleet_folder.id, 'partner_id': self.manager_2.partner_id.id, 'role': 'edit'},
        ])
        attachment_txt_test = self.env['ir.attachment'].with_user(self.manager_1).create({
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'fleet.vehicle',
            'res_id': self.fleet_vehicle.id,
        })
        document = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
        self.assertTrue(document.exists(), "It should have created a document")
        self.assertEqual(document.res_id, self.fleet_vehicle.id, "fleet record linked to the document ")
        self.assertEqual(document.owner_id, self.manager_1, "default document owner is the current user")
        self.assertEqual(document.res_model, self.fleet_vehicle._name, "fleet model linked to the document")
        self.assertTrue(document.is_access_via_link_hidden)
        self.assertEqual(document.access_internal, 'none')
        self.assertEqual(document.access_via_link, 'none')
        access = document.access_ids
        self.assertEqual(len(access), 2, "The access should have been propagated")

        document.with_user(self.manager_2).name

        with self.assertRaises(AccessError):
            document.with_user(self.user).name

    def test_disable_fleet_centralize_option(self):
        """
        Make sure that the document is not created when your Fleet Centralize is disabled.

        Test Case:
        =========
            - Disable the option Centralize your Fleet' documents option
            - Add an attachment to a fleet vehicle
            - Check whether the document is created or not
        """
        company = self.env.user.company_id
        company.documents_fleet_settings = False

        attachment_txt_test = self.env['ir.attachment'].create({
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'fleet.vehicle',
            'res_id': self.fleet_vehicle.id,
        })
        document = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
        self.assertFalse(document.exists(), 'the document should not exist')
