# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="


@tagged("post_install", "-at_install")
class TestDocumentDeletion(HttpCase):

    def test_delete_folder_and_documents_tour(self):
        folder = self.env['documents.document'].create({
            "type": "folder",
            "name": "Folder1",
            "owner_id": self.env.ref('base.user_root').id,
            "access_internal": "edit",
        })
        document = self.env['documents.document'].create({
            'datas': GIF,
            'name': "Chouchou",
            'folder_id': folder.id,
            'mimetype': 'image/gif',
            'owner_id': self.env.user.id,
        })
        folder_copy = folder
        document_copy = document
        self.start_tour(f"/odoo/documents/{folder.access_token}", 'document_delete_tour', login='admin')
        self.assertTrue(folder_copy.exists(), "The folder should still exist")
        self.assertFalse(document_copy.exists(), "The document should not exist anymore")
