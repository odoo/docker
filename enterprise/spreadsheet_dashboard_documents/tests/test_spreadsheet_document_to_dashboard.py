import base64
import json

from uuid import uuid4
from odoo.tests.common import TransactionCase

class TestSpreadsheetDocumentToDashboard(TransactionCase):
    def test_create_wizard(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        document = self.env["documents.document"].create(
            {
                "name": "a document",
                "spreadsheet_data": r'{"sheets": []}',
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        wizard = self.env["spreadsheet.document.to.dashboard"].create(
            {
                "name": "a dashboard",
                "document_id": document.id,
                "dashboard_group_id": group.id,
                "group_ids": self.env.ref("documents.group_documents_user")
            }
        )
        next_action = wizard.create_dashboard()
        dashboard_id = next_action["params"]["dashboard_id"]
        dashboard = self.env["spreadsheet.dashboard"].browse(dashboard_id)
        self.assertEqual(dashboard.name, "a dashboard")
        self.assertEqual(dashboard.group_ids, self.env.ref("documents.group_documents_user"))
        self.assertEqual(dashboard.dashboard_group_id, group)
        self.assertEqual(
            dashboard.spreadsheet_data,
            '{"sheets": []}',
        )
        self.assertEqual(
            next_action,
            {
                "type": "ir.actions.client",
                "tag": "action_spreadsheet_dashboard",
                "name": "a dashboard",
                "params": {
                    "dashboard_id": dashboard_id,
                },
            },
        )

    def test_create_wizard_with_default_values(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        document = self.env["documents.document"].create(
            {
                "name": "a document",
                "spreadsheet_data": r'{"sheets": []}',
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        wizard = self.env["spreadsheet.document.to.dashboard"].create(
            {
                "document_id": document.id,
                "dashboard_group_id": group.id,
            }
        )
        next_action = wizard.create_dashboard()
        dashboard_id = next_action["params"]["dashboard_id"]
        dashboard = self.env["spreadsheet.dashboard"].browse(dashboard_id)
        self.assertEqual(dashboard.name, "a document")
        self.assertEqual(dashboard.group_ids, self.env.ref("base.group_user"))
        self.assertEqual(dashboard.dashboard_group_id, group)
        self.assertEqual(
            dashboard.spreadsheet_data,
            '{"sheets": []}',
        )
        self.assertEqual(
            next_action,
            {
                "type": "ir.actions.client",
                "tag": "action_spreadsheet_dashboard",
                "name": "a document",
                "params": {
                    "dashboard_id": dashboard_id,
                },
            },
        )

    def test_add_spreadsheet_to_dashboard(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        document = self.env["documents.document"].create(
            {
                "name": "a document",
                "spreadsheet_data": r'{"sheets": []}',
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        snapshot = base64.b64encode(b'{"sheets": [{"name": "a sheet"}]}')
        document.spreadsheet_snapshot = snapshot
        revision = self.env["spreadsheet.revision"].create(
            {
                "commands": '{"type": "REMOTE_REVISION", "commands":[]}',
                "res_id": document.id,
                "res_model": "documents.document",
                "revision_uuid": "a revision id",
            }
        )
        self.env["spreadsheet.dashboard"].add_document_spreadsheet_to_dashboard(group.id, document.id)
        self.assertEqual(len(group.dashboard_ids), 1)
        dashboard = group.dashboard_ids[0]
        self.assertEqual(dashboard.name, document.name)
        self.assertEqual(dashboard.spreadsheet_snapshot, document.spreadsheet_snapshot)
        self.assertEqual(dashboard.spreadsheet_snapshot, snapshot)
        self.assertEqual(dashboard.spreadsheet_binary_data, document.datas)
        dashboard_revision = dashboard.spreadsheet_revision_ids[0]
        self.assertEqual(dashboard_revision.revision_uuid, revision.revision_uuid)
        self.assertEqual(dashboard_revision.res_id, dashboard.id)
        self.assertEqual(dashboard_revision.res_model, "spreadsheet.dashboard")

    def test_action_open_new_dashboard(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        action = self.env["spreadsheet.dashboard"].action_open_new_dashboard(group.id)
        dashboard_id = action["params"]["spreadsheet_id"]
        dashboard = self.env["spreadsheet.dashboard"].browse(dashboard_id)
        self.assertTrue(dashboard.exists())
        self.assertEqual(dashboard.name, "Untitled dashboard")
        self.assertEqual(dashboard.spreadsheet_binary_data, dashboard._empty_spreadsheet_data_base64())
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "action_edit_dashboard")

    def test_create_dashboard_and_archive_document(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        document = self.env["documents.document"].create(
            {
                "name": "a document",
                "spreadsheet_data": r'{"sheets": []}',
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        wizard = self.env["spreadsheet.document.to.dashboard"].create(
            {
                "name": "a dashboard",
                "document_id": document.id,
                "dashboard_group_id": group.id,
                "group_ids": self.env.ref("documents.group_documents_user")
            }
        )
        wizard.create_dashboard()
        self.assertFalse(document.active, "The original document should be archived")

    def test_create_dashboard_wizard_moves_comments(self):
        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        data = {
            "sheets": [{
                "comments": [
                    {"A1": {"threadId": 1, "isResolved": False}}
                ]
            }],
        }
        document = self.env["documents.document"].create(
            {
                "name": "a document",
                "spreadsheet_data": json.dumps(data),
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        thread = self.env["spreadsheet.cell.thread"].create([{"document_id": document.id}])
        wizard = self.env["spreadsheet.document.to.dashboard"].create(
            {
                "name": "a dashboard",
                "document_id": document.id,
                "dashboard_group_id": group.id,
                "group_ids": self.env.ref("documents.group_documents_user")
            }
        )
        next_action = wizard.create_dashboard()
        dashboard_id = next_action["params"]["dashboard_id"]
        dashboard = self.env["spreadsheet.dashboard"].browse(dashboard_id)

        self.assertEqual(document.spreadsheet_data, '{"sheets": [{"comments": {}}]}')
        self.assertEqual(thread.document_id.id, False)

        self.assertDictEqual(json.loads(dashboard.spreadsheet_data), data)
        self.assertEqual(thread.dashboard_id, dashboard)

    def test_add_spreadsheet_to_dashboard_purges_comments(self):
        """
        create a document with comments
        -> the dashboard contains the comments
        -> the comments are removed from the document data
        -> the comments are linked to the dashboard
        """

        group = self.env["spreadsheet.dashboard.group"].create(
            {"name": "a group"}
        )
        data = {
            "sheets": [{
                "comments": [
                    {"A1": {"threadId": 1, "isResolved": False}}
                ]
            }],
        }
        document = self.env["documents.document"].create(
            {
                "name": "a document",
                "spreadsheet_data": json.dumps(data),
                "handler": "spreadsheet",
                "mimetype": "application/o-spreadsheet",
            }
        )
        document._dispatch_command(
            {
                "type": "ADD_COMMENT_THREAD",
                "sheetId": "sh1",
                "col": 0,
                "row": 1,
                "threadId": 2,
            }
        )
        document.spreadsheet_snapshot = base64.b64encode(json.dumps(data).encode())

        self.env["spreadsheet.dashboard"].add_document_spreadsheet_to_dashboard(group.id, document.id)
        self.assertEqual(len(group.dashboard_ids), 1)
        dashboard = group.dashboard_ids[0]
        self.assertEqual(dashboard.spreadsheet_data, '{"sheets": [{"comments": {}}]}')
        comment_revision = json.loads(dashboard.spreadsheet_revision_ids[0].commands)
        self.assertEqual(comment_revision["commands"], [])
