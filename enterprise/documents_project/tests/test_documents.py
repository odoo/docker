# -*- coding: utf-8 -*-

import base64

from odoo.exceptions import UserError
from odoo.tests.common import users

from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments
from odoo.addons.project.tests.test_project_base import TestProjectCommon

GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
TEXT = base64.b64encode(bytes("workflow bridge project", 'utf-8'))


class TestDocumentsBridgeProject(TestProjectCommon, TransactionCaseDocuments):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.document_txt_2 = cls.env['documents.document'].create({
            'datas': TEXT,
            'name': 'file2.txt',
            'mimetype': 'text/plain',
            'folder_id': cls.folder_a_a.id,
        })
        cls.pro_admin = cls.env['res.users'].create({
            'name': 'Project Admin',
            'login': 'proj_admin',
            'email': 'proj_admin@example.com',
            'groups_id': [(4, cls.env.ref('project.group_project_manager').id)],
        })

    def test_archive_folder_on_projects_unlinked(self):
        """
        Projects folders should be archived if every related projects have been unlinked.
        """
        folder_1, folder_2, folder_3, folder_4 = self.env['documents.document'].create(
            [{'name': f'F{i}', 'type': 'folder'} for i in range(4)]
        )

        (
            project_0, project_1, project_2, project_3,
            project_4, project_5, project_6, _,
        ) = self.env['project.project'].create([
            {'name': f'p{i}', 'documents_folder_id': folder.id}
            for i, folder in enumerate([folder_1] * 4 + [folder_2] * 3 + [folder_3])
        ])

        cases = [
            (
                project_1 | project_4,
                folder_1 | folder_2 | folder_3 | folder_4,
                self.env['documents.document']
            ), (
                project_2,
                folder_1 | folder_2 | folder_3 | folder_4,
                self.env['documents.document']
            ), (
                project_0 | project_3 | project_5 | project_6,
                folder_3 | folder_4,
                folder_1 | folder_2
            ),
        ]

        count_start = self.env['documents.document'].search_count([('active', '=', True)])

        for projects_to_unlink, active_folders, inactive_folders in cases:
            with self.subTest(projects_to_unlink=projects_to_unlink, active_folders=active_folders, inactive_folders=inactive_folders):
                projects_to_unlink.unlink()
                self.assertTrue(all(active_folders.mapped('active')))
                self.assertFalse(any(inactive_folders.mapped('active')))

        count_end = self.env['documents.document'].search_count([('active', '=', True)])
        self.assertEqual(count_end, count_start - 2)

    def test_bridge_folder_workflow(self):
        """
        tests the create new business model (project).

        """
        self.assertEqual(self.document_txt.res_model, 'documents.document', "failed at default res model")
        self.env['documents.document'].action_folder_embed_action(
            self.document_txt.folder_id.id,
            self.env.ref('documents_project.ir_actions_server_create_project_task').id
        )
        create_task_embedded_action = self.document_txt.available_embedded_actions_ids
        self.assertEqual(len(create_task_embedded_action), 1)
        self.document_txt.action_create_project_task()
        self.assertEqual(self.document_txt.res_model, 'project.task', "failed at workflow_bridge_documents_project"
                                                                      " new res_model")
        task = self.env['project.task'].search([('id', '=', self.document_txt.res_id)])
        self.assertTrue(task.exists(), 'failed at workflow_bridge_documents_project task')
        self.assertEqual(self.document_txt.res_id, task.id, "failed at workflow_bridge_documents_project res_id")

    def test_bridge_parent_folder(self):
        """
        Tests the "Parent Workspace" setting
        """
        parent_folder = self.env.ref('documents_project.document_project_folder')
        self.assertEqual(self.project_pigs.documents_folder_id.folder_id, parent_folder, "The workspace of the project should be a child of the 'Projects' workspace.")

    def test_bridge_project_project_settings_on_write(self):
        """
        Makes sure the settings apply their values when an document is assigned a res_model, res_id
        """

        attachment_txt_test = self.env['ir.attachment'].create({
            'datas': TEXT,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
        })
        attachment_gif_test = self.env['ir.attachment'].create({
            'datas': GIF,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'res_model': 'project.task',
            'res_id': self.task_1.id,
        })

        txt_doc = self.env['documents.document'].search([('attachment_id', '=', attachment_txt_test.id)])
        gif_doc = self.env['documents.document'].search([('attachment_id', '=', attachment_gif_test.id)])

        self.assertEqual(txt_doc.folder_id, self.project_pigs.documents_folder_id, 'the text test document should have a folder')
        self.assertEqual(gif_doc.folder_id, self.project_pigs.documents_folder_id, 'the gif test document should have a folder')

    def test_project_document_count(self):
        projects = self.project_pigs | self.project_goats
        self.assertEqual(self.project_pigs.document_count, 0)
        self.document_txt.write({
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
        })
        projects.invalidate_recordset()
        self.assertEqual(self.project_pigs.document_count, 1, "The documents linked to the project should be taken into account.")
        self.env['documents.document'].create({
            'datas': GIF,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a_a.id,
            'res_model': 'project.task',
            'res_id': self.task_1.id,
        })
        projects.invalidate_recordset()
        self.assertEqual(self.project_pigs.document_count, 2, "The documents linked to the tasks of the project should be taken into account.")

    def test_project_document_search(self):
        # 1. Linking documents to projects/tasks
        documents_linked_to_task = self.env['documents.document'].search([('res_model', '=', 'project.task')])
        documents_linked_to_task_or_project = self.env['documents.document'].search([('res_model', '=', 'project.project')]) | documents_linked_to_task
        projects = self.project_pigs | self.project_goats
        self.assertEqual(projects[0].document_count, 0, "No project should have document linked to it initially")
        self.assertEqual(projects[1].document_count, 0, "No project should have document linked to it initially")
        self.document_txt.write({
            'res_model': 'project.project',
            'res_id': projects[0].id,
        })
        self.document_txt_2.write({
            'res_model': 'project.project',
            'res_id': projects[1].id,
        })
        doc_gif = self.env['documents.document'].create({
            'datas': GIF,
            'name': 'fileText_test.txt',
            'mimetype': 'text/plain',
            'folder_id': self.folder_a_a.id,
            'res_model': 'project.task',
            'res_id': self.task_1.id,
        })

        # 2. Project_id search tests
        # docs[0] --> projects[0] "Pigs"
        # docs[1] --> projects[1] "Goats"
        # docs[2] --> task "Pigs UserTask" --> projects[0] "Pigs"
        docs = self.document_txt + self.document_txt_2 + doc_gif
        # Needed for `in` query leafs
        docs.flush_recordset()
        search_domains = [
            [('project_id', 'ilike', 'pig')],
            [('project_id', '=', 'pig')],
            [('project_id', '!=', 'Pigs')],
            [('project_id', '=', projects[0].id)],
            [('project_id', '!=', False)],
            [('project_id', '=', True)],
            [('project_id', '=', False)],
            [('project_id', 'in', projects.ids)],
            [('project_id', '!=', projects[0].id)],
            [('project_id', 'not in', projects.ids)],
            ['|', ('project_id', 'in', [projects[1].id]), ('project_id', '=', 'Pigs')],
        ]
        expected_results = [
            docs[0] + docs[2],
            self.env['documents.document'],
            docs[1] + documents_linked_to_task_or_project,
            docs[0] + docs[2],
            docs[0] + docs[1] + docs[2] + documents_linked_to_task_or_project,
            docs[0] + docs[1] + docs[2] + documents_linked_to_task_or_project,
            (self.env['documents.document'].search([]) - docs[0] - docs[1] - docs[2] - documents_linked_to_task_or_project),
            docs[0] + docs[1] + docs[2],
            docs[1] + documents_linked_to_task_or_project,
            documents_linked_to_task_or_project,
            docs[0] + docs[1] + docs[2],
        ]
        for domain, result in zip(search_domains, expected_results):
            self.assertEqual(self.env['documents.document'].search(domain), result, "The result of the search on the field project_id/task_id is incorrect (domain used: %s)" % domain)

        # 3. Task_id search tests
        task_2 = self.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Goats UserTask',
            'project_id': projects[1].id})

        self.document_txt.write({
            'res_model': 'project.task',
            'res_id': task_2.id,
        })
        # docs[0] --> tasks[1]  "Goats UserTask"
        # docs[2] --> tasks[0] "Pigs UserTask"
        tasks = self.task_1 | task_2
        self.env.flush_all()
        search_domains = [
            [('task_id', 'ilike', 'pig')],
            [('task_id', '=', 'pig')],
            [('task_id', '!=', 'Pigs UserTask')],
            [('task_id', '=', tasks[1].id)],
            [('task_id', '!=', False)],
            [('task_id', '=', False)],
            [('task_id', 'not in', tasks.ids)],
            ['&', ('task_id', 'in', tasks.ids), '!', ('task_id', 'ilike', 'goats')],
        ]
        expected_results = [
            docs[2],
            self.env['documents.document'],
            docs[0] + documents_linked_to_task,
            docs[0],
            docs[0] + docs[2] + documents_linked_to_task,
            (self.env['documents.document'].search([]) - docs[0] - docs[2] - documents_linked_to_task),
            documents_linked_to_task,
            docs[2],
        ]
        for domain, result in zip(search_domains, expected_results):
            self.assertEqual(self.env['documents.document'].search(domain), result, "The result of the search on the field project_id/task_id is incorrect (domain used: %s)" % domain)

    def test_project_folder_creation(self):
        project = self.env['project.project'].create({
            'name': 'Project',
            'use_documents': False,
        })
        self.assertFalse(project.documents_folder_id, "A project created with the documents feature disabled should have no workspace")
        project.use_documents = True
        self.assertTrue(project.documents_folder_id, "A workspace should be created for the project when enabling the documents feature")

        documents_folder = project.documents_folder_id
        project.use_documents = False
        self.assertTrue(project.documents_folder_id, "The project should keep its workspace when disabling the feature")
        project.use_documents = True
        self.assertEqual(documents_folder, project.documents_folder_id, "No workspace should be created when enablind the documents feature if the project already has a workspace")

    def test_project_task_access_document(self):
        """
        Tests that 'MissingRecord' error should not be rasied when trying to switch
        workspace for a non-existing document.

        - The 'active_id' here is the 'id' of a non-existing document.
        - We then try to access 'All' workspace by calling the 'search_panel_select_range'
            method. We should be able to access the workspace.
        """
        missing_id = self.env['documents.document'].search([], order='id DESC', limit=1).id + 1
        result = self.env['documents.document'].with_context(
            active_id=missing_id, active_model='project.task').search_panel_select_range('folder_id')
        self.assertTrue(result)

    def test_copy_project(self):
        """
        When duplicating a project, there should be exactly one copy of the folder linked to the project.
        If there is the `no_create_folder` context key, then the folder should not be copied (note that in normal flows,
        when this context key is used, it is expected that a folder will be copied/created manually, so that we don't
        end up with a project having the documents feature enabled but no folder).
        """
        last_folder_id = self.env['documents.document'].search([('type', '=', 'folder')], order='id desc', limit=1).id
        self.project_pigs.copy()
        new_folder = self.env['documents.document'].search([('type', '=', 'folder'), ('id', '>', last_folder_id)])
        self.assertEqual(len(new_folder), 1, "There should only be one new folder created.")
        self.project_goats.with_context(no_create_folder=True).copy()
        self.assertEqual(self.env['documents.document'].search_count(
            [('type', '=', 'folder'), ('id', '>', new_folder.id)], limit=1),
            0,
            "There should be no new folder created."
        )

    def test_propagate_document_name_task(self):
        """
        This test will check that the document's name and partner fields are propagated to its tasks on creation
        """
        test_partner = self.env['res.partner'].create({'name': 'TestPartner'})
        self.document_txt.write({'partner_id': test_partner.id})
        self.document_txt.action_create_project_task()

        task = self.env['project.task'].browse(self.document_txt.res_id)

        self.assertEqual(task.name, self.document_txt.name, "The task's name and the document's name should be the same")
        self.assertEqual(task.partner_id, self.document_txt.partner_id, "The task's partner and the document's partner should be the same")

    @users('proj_admin')
    def test_rename_project(self):
        """
        When renaming a project, the corresponding folder should be renamed as well.
        Even when the user does not have write access on the folder, the project should be able to rename it.
        """
        new_name = 'New Name'
        self.project_pigs.with_user(self.env.user).name = new_name
        self.assertEqual(self.project_pigs.documents_folder_id.name, new_name, "The folder should have been renamed along with the project.")

    def test_delete_project_folder(self):
        """
        It should not be possible to delete the "Projects" folder.
        """
        project_folder = self.env.ref('documents_project.document_project_folder')
        with self.assertRaises(UserError, msg="It should not be possible to delete the 'Projects' folder"):
            project_folder.unlink()

        current = project_folder
        for i in range(3):
            current.folder_id = self.env['documents.document'].create({
                "name": f"Ancestor Test {i}",
                "type": "folder",
            })
            current = current.folder_id

        with self.assertRaises(UserError, msg="It should not be possible to delete an ancestor of the 'Projects' folder"):
            current.unlink()

    @users('proj_admin')
    def test_sync_project_privacy_visibility_access_internal(self):
        self.assertEqual(self.document_txt_2.access_internal, 'view')

        self.project_pigs.privacy_visibility = 'followers'

        self.document_txt_2.write({
            'res_model': 'project.project',
            'res_id': self.project_pigs.id,
        })
        self.assertEqual(self.document_txt_2.access_internal, 'none')

        self.project_pigs.invalidate_recordset()
        self.assertIn(self.document_txt_2, self.project_pigs.document_ids)

        self.project_pigs.privacy_visibility = 'employees'
        self.assertEqual(self.document_txt_2.access_internal, 'edit')
        self.project_pigs.privacy_visibility = 'followers'
        self.assertEqual(self.document_txt_2.access_internal, 'none')

        # Now again from a task link
        self.document_txt_2.write({
            'res_model': 'documents.document',
            'res_id': self.document_txt_2.id,
        })
        self.assertEqual(self.document_txt_2.access_internal, 'none')
        self.project_pigs.privacy_visibility = 'employees'
        self.document_txt_2.write({
            'res_model': 'project.task',
            'res_id': self.task_1.id,
        })
        self.assertEqual(self.document_txt_2.access_internal, 'edit')
        self.project_pigs.invalidate_recordset()
        self.assertIn(self.document_txt_2, self.project_pigs.document_ids)
        self.project_pigs.privacy_visibility = 'followers'
        self.assertEqual(self.document_txt_2.access_internal, 'none')
