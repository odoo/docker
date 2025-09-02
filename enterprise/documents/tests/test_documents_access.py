import datetime

from odoo import Command, fields
from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import mute_logger


class TestDocumentsAccess(TransactionCaseDocuments):

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_type_internal(self):
        """Check that the 'internal' access_type_role works as expected."""
        self.assertEqual(self.folder_a.access_internal, 'view')
        self._assert_no_members(self.folder_a)
        self.assertTrue(self.public_user._is_public())
        self.assertTrue(self.portal_user._is_portal())

        self._assert_raises_check_access_rule(self.folder_a.with_user(self.public_user))
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.portal_user))
        self.folder_a.with_user(self.internal_user).check_access('read')
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.internal_user), 'write')

        self.folder_a.access_internal = 'edit'
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.public_user))
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.portal_user))
        self.folder_a.with_user(self.internal_user).check_access('write')

        self.assertTrue(self.env['documents.document'].search([('id', '=', self.folder_a.id)]))
        self.assertFalse(self.env['documents.document'].with_user(self.portal_user).search([('id', '=', self.folder_a.id)]))

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_from_documents_access(self):
        """Check recursive access to documents via documents.access records."""
        self.assertEqual(self.folder_a.access_internal, 'view')
        self.assertEqual(self.folder_a.access_via_link, 'none')
        self.assertEqual(self.folder_a_a.access_internal, 'view')
        self.assertEqual(self.folder_a_a.access_via_link, 'none')

        self._assert_no_members(self.folder_a)
        self.assertTrue(self.portal_user._is_portal())

        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_a_as_portal = self.folder_a_a.with_user(self.portal_user)
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)

        self._assert_raises_check_access_rule(folder_a_as_portal)
        self._assert_raises_check_access_rule(folder_a_a_as_portal)

        portal_access = self.env['documents.access'].create({
            'document_id': self.folder_a.id,
            'partner_id': self.portal_user.partner_id.id,
            'role': 'view',
        })
        folder_a_as_internal.check_access('read')

        self._assert_raises_check_access_rule(folder_a_as_internal, 'write')
        folder_a_as_portal.check_access('read')
        self._assert_raises_check_access_rule(folder_a_a_as_portal, 'read', 'No access given to A-A')
        self._assert_raises_check_access_rule(folder_a_as_portal, 'write')

        portal_access.role = 'edit'
        folder_a_as_portal.check_access('write')

        self.folder_a.access_internal = 'none'

        self._assert_raises_check_access_rule(folder_a_as_internal)
        folder_a_as_portal.check_access('write')

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_from_past_access(self):
        """Check recursive access to documents via documents.log records."""
        self.folder_a.access_via_link = 'view'
        self.folder_a.access_internal = 'none'
        self.folder_a_a.access_via_link = 'view'
        self.folder_a_a.access_internal = 'none'

        self._assert_no_members(self.folder_a)
        self.assertTrue(self.portal_user._is_portal())

        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_a_as_portal = self.folder_a_a.with_user(self.portal_user)
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)
        self.assertEqual(self.folder_a.access_ids.partner_id, self.doc_user.partner_id)  # Owner's log
        self._assert_raises_check_access_rule(folder_a_as_portal)
        self.env['documents.access'].create({
            'document_id': self.folder_a.id,
            'partner_id': self.portal_user.partner_id.id,
            'last_access_date': fields.Datetime.now(),
        })
        self._assert_raises_check_access_rule(folder_a_as_internal)
        folder_a_as_portal.check_access('read')
        folder_a_a_as_portal.check_access('read')
        self.assertEqual(folder_a_as_portal.user_permission, 'view')
        self._assert_raises_check_access_rule(folder_a_as_portal, 'write')
        self.folder_a.access_via_link = 'edit'
        folder_a_as_portal.check_access('write')
        self._assert_raises_check_access_rule(folder_a_a_as_portal, 'write')

        self.folder_a.access_via_link = 'none'
        self._assert_raises_check_access_rule(folder_a_as_portal)
        self._assert_raises_check_access_rule(folder_a_a_as_portal)  # logged access it to parent, now mute.

    def test_access_rights_inherited_on_create(self):
        (self.folder_a + self.folder_b).write({
            'access_via_link': 'none',
            'access_internal': 'none'
        })
        self._assert_no_members(self.folder_a + self.folder_b)
        folder_a1 = self.env['documents.document'].create(
            {'name': 'Folder A1', 'folder_id': self.folder_a.id, 'type': 'folder'}
        )
        # Owner of parent folder is given membership
        self.assertEqual(folder_a1.access_ids.partner_id, self.folder_a.owner_id.partner_id)
        self.assertEqual(folder_a1.access_internal, 'none')
        self.assertEqual(folder_a1.access_via_link, 'none')
        self.folder_a.access_internal = 'view'
        self.assertEqual(len(self.folder_a.access_ids), 1)  # owner's log
        self.folder_a.action_update_access_rights(partners={self.portal_user.partner_id.id: ('view', False)})
        self.assertEqual(len(self.folder_a.access_ids), 2)  # owner's log + portal member
        self.folder_b.access_via_link = 'edit'
        self.folder_b.action_update_access_rights(partners={self.portal_user.partner_id.id: (False, False)})
        folder_a2, folder_b1 = self.env['documents.document'].create([
            {'name': 'Folder A2', 'folder_id': self.folder_a.id, 'type': 'folder'},
            {'name': 'Folder B1', 'folder_id': self.folder_b.id, 'type': 'folder'},
        ])
        self.assertEqual(len(folder_a2.access_ids), 2)  # inherited portal member + folder_a's owner
        self.assertEqual(folder_a2.access_ids.partner_id, (self.portal_user + self.doc_user).partner_id)
        self.assertEqual(folder_a2.access_internal, 'view')
        self.assertEqual(folder_a2.access_via_link, 'none')

        self.assertEqual(folder_b1.access_ids.partner_id, self.doc_user.partner_id)  # parent's owner (!= from child)
        self.assertEqual(folder_b1.access_internal, 'none')
        self.assertEqual(folder_b1.access_via_link, 'edit')

        folder_a3, folder_a4 = self.env['documents.document'].create([
            {'name': 'Folder A3', 'folder_id': self.folder_a.id, 'type': 'folder', 'access_ids': False},
            {'name': 'Folder A4', 'folder_id': self.folder_a.id, 'type': 'folder',
             'access_ids': [
                Command.create({'partner_id': self.internal_user.partner_id.id, 'role': 'view'})
             ]},
        ])
        self.assertFalse(folder_a3.access_ids)
        self.assertEqual(len(folder_a4.access_ids), 1)
        self.assertEqual(folder_a4.access_ids.partner_id, self.internal_user.partner_id)

        self.folder_a.access_internal = 'edit'
        self.folder_a.access_via_link = 'view'

        # Create another log
        self.env['documents.access'].create({
            'document_id': self.folder_a.id,
            'partner_id': self.internal_user.partner_id.id,
            'last_access_date': fields.Datetime.now(),
        })
        self.assertEqual(len(self.folder_a.access_ids), 3)
        folder_a5 = self.env['documents.document'] \
            .with_context(default_access_internal='view', default_folder_id=self.folder_a.id) \
            .create({'name': 'Folder A5', 'type': 'folder'})
        self.assertEqual(len(folder_a5.access_ids), 2)
        # Inherited from member + owner, not logged access
        self.assertEqual(folder_a5.access_ids.partner_id, (self.portal_user + self.doc_user).partner_id)
        self.assertEqual(folder_a5.access_internal, 'edit')
        self.assertEqual(folder_a5.access_via_link, 'view')

        folder_a6 = self.env['documents.document'] \
            .with_context(default_access_internal='view', default_folder_id=self.folder_a.id) \
            .create({'name': 'Folder A6', 'type': 'folder', 'access_ids': False, 'access_internal': 'none'})
        self.assertFalse(folder_a6.access_ids)
        self.assertEqual(folder_a6.access_internal, 'none')
        self.assertEqual(folder_a6.access_via_link, 'view')

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_owner(self):
        self.folder_a.write({
            'access_via_link': 'none',
            'access_internal': 'none'
        })
        self._assert_no_members(self.folder_a)
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.internal_user))
        self.assertEqual(self.folder_a.owner_id, self.doc_user)
        self.folder_a.with_user(self.doc_user).check_access('read')
        self.folder_a.with_user(self.doc_user).check_access('write')

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_documents_access_cu(self):
        secret = self.env['documents.document'].create({
            'access_internal': 'none',
            'access_via_link': 'none',
            'name': 'secret',
        })
        public = self.env['documents.document'].create({
            'access_internal': 'edit',
            'access_via_link': 'none',
            'name': 'secret',
        })
        secret_id = secret.id
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            secret.with_user(self.doc_user).name

        with self.assertRaises(AccessError):
            self.env['documents.access'].with_user(self.doc_user).create({
                'role': 'edit',
                'document_id': secret_id,
                'partner_id': self.doc_user.partner_id.id,
            })

        with self.assertRaises(AccessError):
            self.env['documents.access'].with_user(self.doc_user).with_context(
                default_document_id=secret_id).create({
                'role': 'edit',
                'partner_id': self.doc_user.partner_id.id,
            })

        access = self.env['documents.access'].with_user(self.doc_user).create({
            'role': 'edit',
            'document_id': public.id,
            'partner_id': self.doc_user.partner_id.id,
        })
        with self.assertRaises(AccessError):
            access.document_id = secret_id

        with self.assertRaises(AccessError):
            access.copy(default={'document_id': secret_id})

        access_admin = self.env['documents.access'].create({
            'role': 'edit',
            'document_id': secret_id,
            'partner_id': self.env.user.partner_id.id,
        })
        with self.assertRaises(AccessError):
            access_admin.with_user(self.doc_user).unlink()

        # check that the user can not upgrade a view access
        access = self.env['documents.access'].create({
            'role': 'view',
            'document_id': secret.id,
            'partner_id': self.doc_user.partner_id.id,
        })
        with self.assertRaises(AccessError):
            access.with_user(self.doc_user).role = 'edit'

        with self.assertRaises(AccessError):
            access.with_user(self.doc_user).expiration_date = datetime.datetime.now()

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_users_drive_is_private(self):
        # Make folder_a a folder in internal users' drive
        self.folder_a.write({
            'access_internal': 'none',
            'access_via_link': 'none',
            'folder_id': False,
            'owner_id': self.internal_user,
        })
        self._assert_no_members(self.folder_a)

        not_authorized = self.doc_user + self.document_manager + self.portal_user
        for not_authorized_user in not_authorized:
            with self.subTest(user=not_authorized_user.name):
                folder_a_with_user = self.folder_a.with_user(not_authorized_user)
                self.assertEqual(self.folder_a.with_user(self.doc_user).user_permission, 'none')
                self.assertFalse(folder_a_with_user.search([('id', '=', self.folder_a.id)]))
                self._assert_raises_check_access_rule(folder_a_with_user)

        def test_authorized_users(authorized_users):
            for authorized_user in authorized_users:
                folder_a = self.folder_a.with_user(authorized_user)
                with self.subTest(user=authorized_user.name, method='compute'):
                    self.assertEqual(folder_a.user_permission, 'edit')
                with self.subTest(user=authorized_user.name, method='search'):
                    self.assertEqual(
                        folder_a.search([('id', '=', folder_a.id), ('user_permission', '=', 'edit')]),
                        folder_a
                    )
                    self.assertEqual(folder_a.search([('id', '=', self.folder_a.id)]), self.folder_a)

        self.document_manager.groups_id |= self.env.ref('documents.group_documents_system')

        test_authorized_users(self.internal_user + self.document_manager)

        self.folder_a.action_update_access_rights(partners={self.portal_user.partner_id: ('edit', False)})
        test_authorized_users(self.portal_user)

        self.folder_a.action_update_access_rights(access_internal='edit')
        test_authorized_users(self.doc_user + self.document_manager)

        self.folder_a.action_update_access_rights(access_internal='view')
        test_authorized_users(self.document_manager)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_action_update_access_rights_partners(self):
        """Check that we can update partners access to a document."""
        self._assert_no_members(self.folder_a)
        portal_user_2 = self.portal_user.copy()

        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_as_portal_2 = self.folder_a.with_user(portal_user_2)
        self._assert_raises_check_access_rule(folder_a_as_portal)
        self._assert_raises_check_access_rule(folder_a_as_portal_2)

        # Make portal and portal 2 viewers, permanently or for one day, resp.
        IN_ONE_DAY = fields.Datetime.now() + datetime.timedelta(days=1)
        partners = {
            self.portal_user.partner_id.id: ('view', False),
            portal_user_2.partner_id.id: ('view', IN_ONE_DAY)
        }
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            self.folder_a.action_update_access_rights(partners=partners)
        folder_a_as_portal.check_access('read')
        folder_a_as_portal_2.check_access('read')
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)

        # Check that expiration was propagated too
        portal_2_a_a_access = self.folder_a_a.access_ids.filtered(
            lambda a: a.partner_id == portal_user_2.partner_id)
        self.assertEqual(len(portal_2_a_a_access), 1)
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_ONE_DAY)
        # Update expiration alone via parent
        IN_12_H = IN_ONE_DAY - datetime.timedelta(hours=12)
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            self.folder_a.action_update_access_rights(partners={portal_user_2.partner_id: ('view', IN_12_H)})
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_12_H)

        # Update role+expiration via parent
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            self.folder_a.action_update_access_rights(partners={portal_user_2.partner_id: ('edit', IN_ONE_DAY)})
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_ONE_DAY)
        self.assertEqual(portal_2_a_a_access.role, 'edit')

        # Update role alone via parent
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            self.folder_a.action_update_access_rights(partners={portal_user_2.partner_id: ('view', None)})
        self.assertEqual(portal_2_a_a_access.expiration_date, IN_ONE_DAY)
        self.assertEqual(portal_2_a_a_access.role, 'view')

        # Make portal viewer of grandchild folder only
        partners = {self.portal_user.partner_id.id: (False, None)}

        self.env.invalidate_all()
        with self.assertQueryCount(8):
            self.folder_a.action_update_access_rights(partners=partners)
            self.assertFalse(self.folder_a.access_ids.filtered(lambda a: a.partner_id == self.portal_user.partner_id))
        self._assert_raises_check_access_rule(folder_a_as_portal, 'read')

        folder_a_a_p = self.env['documents.document'].create({
            'type': 'folder',
            'name': "A cool name",
            'folder_id': self.folder_a_a.id,
        })

        partners = {self.portal_user.partner_id.id: ('view', False)}
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            folder_a_a_p.action_update_access_rights(partners=partners)

        # Make portal and internal editors of parent folder, this should propagate down
        partners = {
            partner_id: ('edit', False)
            for partner_id in (self.portal_user | self.internal_user).partner_id.ids
        }
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            self.folder_a.action_update_access_rights(partners=partners)
        folder_a_as_portal.check_access('write')
        folder_a_a_as_portal = self.folder_a_a.with_user(self.portal_user)
        folder_a_a_as_portal.check_access('write')
        folder_a_as_internal.check_access('write')

        self._assert_raises_check_access_rule(folder_a_as_portal_2, 'write')

        # Remove portal 2 access
        portal_2_partner_id = portal_user_2.partner_id.id
        self.env.invalidate_all()
        with self.assertQueryCount(5):
            self.folder_a.action_update_access_rights(partners={portal_2_partner_id: (False, False)})
        self._assert_raises_check_access_rule(folder_a_as_portal_2)

        # Add portal 2 access to 1st level child and remove from 2nd
        self.env.invalidate_all()
        with self.assertQueryCount(4):
            self.folder_a_a.action_update_access_rights(partners={portal_2_partner_id: ('view', False)})
        folder_a_a_p.action_update_access_rights(partners={portal_user_2.partner_id.id: (False, None)})
        self.assertFalse(folder_a_a_p.access_ids.filtered(lambda a: a.partner_id == portal_user_2.partner_id))

        # check that the accesses are propagated on the documents even if they are in the trash
        folder_a_a_p.action_archive()
        self.folder_a_a.action_update_access_rights(partners={portal_user_2.partner_id.id: ('edit', None)})
        self.assertEqual(folder_a_a_p.access_ids.filtered(lambda a: a.partner_id == portal_user_2.partner_id).role, 'edit')

    def test_action_update_access_rights_internal_propagation(self):
        self.assertEqual(set((self.folder_b + self.document_gif).mapped('access_internal')), {'view'})
        self.folder_b.action_update_access_rights(access_internal='none')
        self.assertEqual(set((self.folder_b + self.document_gif).mapped('access_internal')), {'none'})

        # check that the accesses are propagated on the documents even if they are in the trash
        self.document_gif.action_archive()
        self.folder_b.action_update_access_rights(access_internal='edit')
        self.assertEqual(set((self.folder_b + self.document_gif).mapped('access_internal')), {'edit'})

        self.document_gif.action_update_access_rights(access_internal='view')
        self.assertEqual((self.folder_b + self.document_gif).mapped('access_internal'), ['edit', 'view'])

    def test_action_update_access_rights_link_propagation(self):
        self.assertEqual(set((self.folder_b + self.document_gif).mapped('access_via_link')), {'none'})
        self.folder_b.action_update_access_rights(access_via_link='view')
        self.assertEqual(set((self.folder_b + self.document_gif).mapped('access_via_link')), {'view'})

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_action_update_access_rights_sudo(self):
        """Test that the action will update rights on restricted access folder when using sudo."""
        self.folder_a.write({
            'access_internal': 'none',
            'access_via_link': 'none',
            'folder_id': False,
            'owner_id': self.document_manager,
        })
        self._assert_no_members(self.folder_a)
        folder_a_as_internal = self.folder_a.with_user(self.internal_user)
        # Members
        with self.assertRaises(AccessError):
            folder_a_as_internal.action_update_access_rights(partners={self.internal_user.partner_id: ('edit', None)})
        folder_a_as_internal.sudo().action_update_access_rights(partners={self.internal_user.partner_id: ('edit', None)})

    def test_action_move_documents(self):
        """Check that documents can be moved to new location and have their rights updated."""
        self.folder_b.write({
            'access_internal': 'none',
            'access_via_link': 'none',
        })
        self.folder_a.write({'access_via_link': 'view'})
        self.folder_a_a.action_move_documents(folder_id=self.folder_b.id)
        self.assertEqual(self.folder_a_a.folder_id, self.folder_b)

        self.folder_b.action_move_documents(folder_id=self.folder_a.id)

        self.assertEqual(self.folder_b.folder_id, self.folder_a)
        self.assertEqual(self.folder_b.access_internal, 'view', 'Internal access should have been updated.')
        self.assertEqual(self.folder_b.access_via_link, 'view', 'link access should have been updated.')

        self.document_gif.folder_id = False
        shortcut = self.folder_b.action_create_shortcut(False)
        self.document_gif.action_move_documents(shortcut.id)
        self.assertEqual(self.document_gif.folder_id, self.folder_b)

        doc_shortcut = self.document_gif.action_create_shortcut(shortcut.id)
        self.assertEqual(doc_shortcut.folder_id, self.folder_b)

        # making a shortcut of a shortcut use the target instead
        shortcut = shortcut.action_create_shortcut(False)
        self.assertEqual(shortcut.shortcut_document_id, self.folder_b)

        self.folder_a.action_update_access_rights(partners={self.internal_user.partner_id.id: ('edit', False)})
        self.folder_b.action_update_access_rights(partners={self.internal_user.partner_id.id: ('view', False)})
        with self.assertRaises(AccessError):
            self.document_gif.with_user(self.internal_user).folder_id = self.folder_a

        with self.assertRaises(AccessError):
            self.document_gif.with_user(self.internal_user).action_move_documents(self.folder_a.id)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_create_document_access(self):
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).name = 'test'

        with self.assertRaises(AccessError):
            self.env['documents.document'].with_user(self.internal_user).create({
                'name': 'folder',
                'folder_id': self.folder_a.id,
                'owner_id': self.internal_user.id,
                'type': 'folder',
            })

        # internal user can create a file on the root
        self.env['documents.document'].with_user(self.internal_user).create({
            'name': 'document',
            'folder_id': False,
            'owner_id': self.internal_user.id,
            'type': 'binary',
        })

        with self.assertRaises(UserError):
            # portal can not be the owner of a document on the root
            self.env['documents.document'].with_user(self.portal_user).create({
                'name': 'document',
                'folder_id': False,
                'owner_id': self.portal_user.id,
                'type': 'binary',
            })

        with self.assertRaises(UserError):
            # and portal can not create a document on the root for an other user
            self.env['documents.document'].with_user(self.portal_user).create({
                'name': 'document',
                'folder_id': False,
                'owner_id': self.env.ref('base.user_root').id,
                'type': 'binary',
            })

        # but in SUDO, portal should be able to create a document on the root
        self.env['documents.document'].with_user(self.portal_user).sudo().create({
            'name': 'document',
            'folder_id': False,
            'owner_id': self.env.ref('base.user_root').id,
            'type': 'binary',
        })

        with self.assertRaises(UserError):
            # even in SUDO, portal can not be set as the owner of a root document
            self.env['documents.document'].with_user(self.portal_user).sudo().create({
                'name': 'document',
                'folder_id': False,
                'owner_id': self.portal_user.id,
                'type': 'binary',
            })

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_restrict_write_on_pinned_folders(self):
        """Check that editing pinned folders is restricted to managers

        Creating inside depends on regular access rights
        """
        odoobot = self.env.ref('base.user_root')
        self.assertFalse(self.folder_a.folder_id)
        self.folder_a.owner_id = odoobot
        self.folder_a.action_update_access_rights(partners={self.internal_user.partner_id.id: ('edit', False)})
        access = self.env['documents.access'].search([
            ('document_id', '=', self.folder_a.id),
            ('partner_id', '=', self.internal_user.partner_id.id),
        ])
        self.assertEqual(len(access), 1)
        self.assertEqual(access.role, 'edit')
        with self.assertRaises(AccessError):  # Un-pin attempt
            self.folder_a.with_user(self.internal_user).folder_id = self.folder_b
        # That's because
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.internal_user), 'write')
        # but user_permission = 'edit' and can create inside
        self.assertEqual(self.folder_a.with_user(self.internal_user).user_permission, 'edit')
        self.env['documents.document'].with_user(self.internal_user).create({
            'type': 'folder', 'name': 'a folder', 'folder_id': self.folder_a.id
        })
        # or create a shortcut inside
        shortcut = self.document_txt.with_user(self.internal_user).action_create_shortcut(
            location_folder_id=self.folder_a.id
        )
        self.assertEqual(shortcut.folder_id, self.folder_a)
        # Managers can unpin by moving to another odoobot folder
        self.folder_b.owner_id = odoobot
        self.folder_a.with_user(self.document_manager).folder_id = self.folder_b
        self.assertFalse(self.folder_a.is_pinned_folder)
        # Or moving to their own drive
        self.folder_a.with_user(self.document_manager).folder_id = False
        self.folder_a.with_user(self.document_manager).owner_id = self.document_manager

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_pin_folder_create(self):
        """Check that a normal user can not create a pinned folder."""
        odoobot = self.env.ref('base.user_root')
        folder = self.env['documents.document'].create({
            'folder_id': False,
            'name': 'folder',
            'owner_id': odoobot.id,
            'type': 'folder',
        })
        self.assertTrue(folder.is_pinned_folder)

        with self.assertRaises(AccessError):
            self.env['documents.document'].with_user(self.internal_user).create({
                'folder_id': False,
                'name': 'folder',
                'owner_id': odoobot.id,
                'type': 'folder',
            })

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_pin_folder_folder_id(self):
        """Check that non-admins cannot (un-)pin company root folders."""
        odoobot = self.env.ref('base.user_root')
        self.assertFalse(self.folder_a.folder_id)

        self.folder_a.owner_id = self.document_manager
        self.folder_a.action_update_access_rights(
            access_internal='none',
            partners={self.internal_user.partner_id.id: ('edit', False)}
        )
        children_access_before = [access_ids.filtered(lambda a: a.role)
                                  for access_ids in self.folder_a.children_ids.mapped(lambda f: f.access_ids)]
        for child_access_before in children_access_before:
            self.assertFalse(self.document_manager.partner_id & child_access_before.partner_id)

        # managers pins from their drive
        self.folder_a.with_user(self.document_manager).action_set_as_company_root()
        self.assertEqual(
            (self.document_manager | self.internal_user).partner_id,
            self.folder_a.access_ids.filtered(lambda a: a.role).partner_id)
        # Manager access was not added on children
        self.assertEqual(
            [access_ids.filtered(lambda a: a.role)
             for access_ids in self.folder_a.children_ids.mapped(lambda f: f.access_ids)],
            children_access_before)

        # internal user cannot write on pinned folders
        self._assert_raises_check_access_rule(self.folder_a.with_user(self.internal_user), 'write')

        self.folder_b.folder_id = False
        self.assertEqual(self.folder_b.owner_id, self.doc_user)
        self.folder_b.action_update_access_rights(
            access_internal='edit',
            partners={self.internal_user.partner_id.id: ('edit', False)}
        )
        children_access_before = [access_ids.filtered(lambda a: a.role)
                                  for access_ids in self.folder_b.children_ids.mapped(lambda f: f.access_ids)]
        for child_access_before in children_access_before:
            self.assertFalse(self.doc_user.partner_id & child_access_before.partner_id)

        # managers can pin accessible folders (here in other user's drive)
        self.folder_b.with_user(self.document_manager).action_set_as_company_root()
        # previous owner is added as member
        self.assertEqual(
            (self.doc_user | self.internal_user).partner_id,
            self.folder_b.access_ids.filtered(lambda a: a.role).partner_id)

        # Previous owner access was not added on children
        self.assertEqual(
            [access_ids.filtered(lambda a: a.role)
             for access_ids in self.folder_b.children_ids.mapped(lambda f: f.access_ids)],
            children_access_before)

        # set_as_company_root changed owner_id
        self.assertEqual((self.folder_a | self.folder_b).owner_id, odoobot)

        # Normal user cannot pin
        self.folder_a.with_user(self.document_manager).owner_id = self.internal_user
        self.folder_a.with_user(self.internal_user).check_access('write')
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).action_set_as_company_root()

        # with SUDO, a normal user can pin a folder
        self.folder_a.with_user(self.internal_user).sudo().action_set_as_company_root()
        # with SUDO, a normal user can move a pinned a folder
        self.folder_a.with_user(self.internal_user).sudo().owner_id = self.internal_user

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_unlink_with_children(self):
        """Check that deletion handles children items and checks access rights

        This is necessary to avoid handling changes of access rights when moving
        records to parent folders, showing them in the trash etc. This is also
        important to make sure that an OdooBot-owned 2nd level folder cannot be
        pinned by deleting its parent
        """
        self.folder_a.action_update_access_rights(access_internal='edit')
        self.folder_a_a.action_update_access_rights(access_internal='none')
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).unlink()
        self.folder_a_a.action_update_access_rights(access_internal='edit')
        self.folder_a.with_user(self.internal_user).unlink()
        self.assertFalse(self.folder_a_a.exists())

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_archiving_with_children(self):
        """Check that archiving handles children items and checks access rights.

        See also ``test_unlink_with_children``
        """
        self.folder_a.action_update_access_rights(access_internal='edit')
        self.folder_a_a.action_update_access_rights(access_internal='none')
        with self.assertRaises(AccessError):
            self.folder_a.with_user(self.internal_user).action_archive()
        self.folder_a_a.action_update_access_rights(access_internal='edit')
        self.folder_a.with_user(self.internal_user).action_archive()
        self.assertFalse(self.folder_a_a.active)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_expiration(self):
        """Check that expired access_ids no longer provide access."""
        self._assert_no_members(self.folder_a)
        self.folder_a.action_update_access_rights(partners={self.portal_user.partner_id.id: ('view', False)})
        folder_a_as_portal = self.folder_a.with_user(self.portal_user)
        folder_a_as_portal.check_access('read')
        first_child_as_portal = folder_a_as_portal.children_ids
        self.folder_a.action_update_access_rights(partners={
            self.portal_user.partner_id.id: ('view', fields.Datetime.now() - datetime.timedelta(days=1))})
        self.assertEqual(len(first_child_as_portal), 1)
        self._assert_raises_check_access_rule(folder_a_as_portal, 'read')
        # As we did update children
        self._assert_raises_check_access_rule(first_child_as_portal, 'read')

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_via_link_from_parent_folder(self):
        """Check that a document accessible via link is accessible to users having access to the parent folder.

        Note that access via link to the parent is only checked if there is an access record (albeit without role).
        This is used to:
         * share a folder with its similarly-configured contents to a public user with a single token
         (incl. download a zip).
         * make files discoverable when navigating the parent folder in the client without creating `access` records
          for every file when 'reading' the folder.
        """
        self._assert_no_members(self.folder_b)
        self.folder_b.action_update_access_rights(access_internal='none', access_via_link='none')  # with propagation
        self.assertEqual(self.folder_b.access_internal, 'none')
        self.assertEqual(self.document_gif.access_internal, 'none')
        self.assertEqual(self.document_txt.access_internal, 'none')
        self.assertEqual(self.document_gif.access_via_link, 'none')
        self.assertEqual(self.document_txt.access_via_link, 'view')
        document_txt_private = self.document_txt.copy()
        document_txt_private.is_access_via_link_hidden = True
        self.assertEqual(document_txt_private.access_via_link, 'view')

        gif_as_internal = self.document_gif.with_user(self.internal_user)
        txt_as_internal = self.document_txt.with_user(self.internal_user)
        txt_private_as_internal = document_txt_private.with_user(self.internal_user)

        self._assert_raises_check_access_rule(gif_as_internal | txt_as_internal, 'read')

        access_values = {'document_id': self.folder_b.id, 'partner_id': self.internal_user.partner_id.id}
        folder_accesses_values = [
            ('internal user access', {'access_internal': 'view'}),
            ('link accessed', {
                'access_via_link': 'view',
                'access_ids': [Command.create(access_values | {'last_access_date': fields.Datetime.now()})]
            }),
            ('member', {'access_ids': [Command.create(access_values | {'role': 'view'})]}),
        ]
        for case_name, folder_access_vals in folder_accesses_values:
            with self.subTest(case_name=case_name):
                self.folder_b.write(folder_access_vals)
                self._assert_raises_check_access_rule(gif_as_internal, 'read')
                self._assert_raises_check_access_rule(txt_private_as_internal, 'read')
                self.assertEqual((gif_as_internal | txt_private_as_internal).mapped('user_permission'), ['none', 'none'])
                self.assertEqual(txt_as_internal.search([('folder_id', '=', self.folder_b.id)]), self.document_txt)
                txt_as_internal.check_access('read')
                if case_name == 'internal user access':  # Difference between internal and portal
                    self._assert_raises_check_access_rule(self.document_txt.with_user(self.portal_user), 'read')

            # cleanup
            self.folder_b.write({'access_internal': 'none', 'access_via_link': 'none'})
            self.folder_b.access_ids.unlink()

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_rights_shortcuts_and_discoverability(self):
        """Check access rights related to shortcuts:

        * A shortcut pointing to a non-accessible document is hidden.
        * A shortcut pointing to a non-accessible document but discoverable with link should be visible.

        See also ``test_access_via_link_from_parent_folder``.
        """
        self._assert_no_members(self.folder_b)
        self.folder_b.action_move_documents(self.folder_a.id)
        self.folder_a.owner_id = self.env.ref('base.user_root')

        self.assertEqual(self.folder_a.access_internal, 'view')
        self.assertEqual(self.document_txt.folder_id, self.folder_b)

        self.folder_a.action_update_access_rights(partners={self.portal_user.partner_id: ('view', False)})
        (self.folder_b + self.document_txt).action_update_access_rights(
            access_internal='none', access_via_link='none', partners={self.portal_user.partner_id: (False, False)})

        self.assertEqual(self.document_txt.with_user(self.portal_user).user_permission, 'none')

        self._assert_raises_check_access_rule(self.document_txt.with_user(self.portal_user), 'read')

        # Create a shortcut to document_txt in folder_a
        shortcut = self.document_txt.action_create_shortcut(location_folder_id=self.folder_a.id)

        self._assert_raises_check_access_rule(shortcut.with_user(self.portal_user), 'read',
                                              "Shortcut shouldn't be visible as source is inaccessible")
        self.assertEqual(shortcut.with_user(self.portal_user).user_permission, 'none')

        docs = self.document_txt + shortcut

        # Neither internal nor manager can't see any one of the two
        self.assertSetEqual(set(docs.with_user(self.internal_user).mapped('user_permission')), {'none'})
        self._assert_raises_check_access_rule(docs.with_user(self.internal_user), 'read')

        self.assertSetEqual(set(docs.with_user(self.document_manager).mapped('user_permission')), {'none'})
        self._assert_raises_check_access_rule(docs.with_user(self.document_manager), 'read')

        # Let internal see both
        self.document_txt.action_update_access_rights(access_internal='view')
        self.assertSetEqual(set(docs.with_user(self.internal_user).mapped('user_permission')), {'view'})
        docs.with_user(self.internal_user).check_access('read')

        # Manager now has edit right
        self.assertSetEqual(set(docs.with_user(self.document_manager).mapped('user_permission')), {'edit'})
        docs.with_user(self.document_manager).check_access('write')

        # Still not portal
        self.assertSetEqual(set(docs.with_user(self.portal_user).mapped('user_permission')), {'none'})
        self._assert_raises_check_access_rule(docs.with_user(self.portal_user), 'read')

        self.document_txt.action_update_access_rights(access_via_link='view', is_access_via_link_hidden=True)
        self.assertEqual(shortcut.access_via_link, 'view')
        self.assertEqual(shortcut.is_access_via_link_hidden, True)
        self._assert_raises_check_access_rule(shortcut.with_user(self.portal_user), 'read',
                                              "Shortcut shouldn't be visible as source is still inaccessible")
        self.assertEqual(shortcut.with_user(self.portal_user).user_permission, 'none')

        self.document_txt.action_update_access_rights(is_access_via_link_hidden=False)
        self.assertEqual(self.document_txt.is_access_via_link_hidden, False)
        self.assertEqual(shortcut.is_access_via_link_hidden, False)
        self.assertEqual(shortcut.with_user(self.portal_user).user_permission, 'view')
        shortcut.with_user(self.portal_user).check_access('read')

        # Shortcut target is still inaccessible, it will be made available when logging access
        self._assert_raises_check_access_rule(self.document_txt.with_user(self.portal_user), 'read')

        # Updating the access on the target update the access on the shortcut itself
        partner = self.env['res.partner'].create({'name': 'Test'})
        shortcut.shortcut_document_id.action_update_access_rights(
            access_internal='edit', partners={partner: ('edit', False)})
        self.assertEqual(shortcut.shortcut_document_id.access_internal, 'edit')
        self.assertEqual(shortcut.access_internal, 'edit')

        access = self.env['documents.access'].search([('partner_id', '=', partner.id)])
        self.assertEqual(len(access), 2)
        self.assertEqual(access.document_id, shortcut | shortcut.shortcut_document_id)

        shortcut.shortcut_document_id.action_update_access_rights(
            access_internal='edit', partners={partner: (False, False)})
        self.assertFalse(access.exists())

        # Check that own shortcut is deleted when access to the target is removed
        # (avoids client fetches on inaccessible previews & others).
        self.folder_a.action_update_access_rights(access_internal='edit')
        self.document_txt.action_update_access_rights(access_internal='view', access_via_link='none')

        # Access via access_internal
        shortcut = self.document_txt.with_user(self.internal_user).action_create_shortcut(
            location_folder_id=self.folder_a.id
        )
        self.assertEqual(shortcut.owner_id, self.internal_user)
        self.document_txt.action_update_access_rights(access_internal='none')
        self.assertEqual(self.document_txt.with_user(self.internal_user).user_permission, 'none')
        self.assertFalse(shortcut.exists())

        # Access via membership
        self.document_txt.action_update_access_rights(
            partners={self.internal_user.partner_id: ('view', False)})
        shortcut = self.document_txt.with_user(self.internal_user).action_create_shortcut(
            location_folder_id=self.folder_a.id
        )
        self.assertEqual(shortcut.owner_id, self.internal_user)
        self.document_txt.action_update_access_rights(partners={self.internal_user.partner_id: (False, False)})
        self.assertFalse(shortcut.exists())

        # Access via ownership
        self.document_txt.owner_id = self.internal_user
        shortcut = self.document_txt.with_user(self.internal_user).action_create_shortcut(
            location_folder_id=self.folder_a.id
        )
        self.assertEqual(shortcut.owner_id, self.internal_user)
        self.document_txt.owner_id = self.document_manager
        self.assertFalse(shortcut.exists())

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_access_rights_shortcuts_propagation(self):
        """Test that we update shortcuts if we have edit access on the document"""
        target = self.env['documents.document'].create({
            'name': 'Target',
            'access_internal': 'edit',
        })

        root = self.env['documents.document'].create({
            'name': 'Root',
            'type': 'folder',
            'access_internal': 'edit',
            'children_ids': [Command.create({
                'name': 'A',
                'type': 'folder',
                'access_internal': 'edit',
                'is_access_via_link_hidden': True,
                'children_ids': [Command.create({
                    'name': 'File 1',
                    'access_internal': 'edit',
                }), Command.create({
                    'name': 'File 2',
                    'access_internal': 'view',
                }), Command.create({
                    'name': 'File 3',
                    'access_internal': 'none',
                    'access_via_link': 'edit',
                    'is_access_via_link_hidden': False,
                }), Command.create({
                    'name': 'Sub-folder',
                    'type': 'folder',
                    'access_internal': 'edit',
                    'children_ids': [Command.create({
                        'name': 'Sub-file',
                        'access_internal': 'edit',
                    })]
                }), Command.create({
                    'name': 'Shortcut',
                    'access_internal': 'edit',
                    'shortcut_document_id': target.id,
                })],
            })],
            'owner_id': self.document_manager.id  # not odoobot
        })

        file_1 = self.env['documents.document'].search([('id', 'child_of', root.id), ('name', '=', 'File 1')])
        file_2 = self.env['documents.document'].search([('id', 'child_of', root.id), ('name', '=', 'File 2')])
        file_3 = self.env['documents.document'].search([('id', 'child_of', root.id), ('name', '=', 'File 3')])
        shortcut = self.env['documents.document'].search([('id', 'child_of', root.id), ('name', '=', 'Shortcut')])
        sub_folder = self.env['documents.document'].search([('id', 'child_of', root.id), ('name', '=', 'Sub-folder')])
        sub_file = self.env['documents.document'].search([('id', 'child_of', root.id), ('name', '=', 'Sub-file')])
        shortcut_1 = file_1.action_create_shortcut(False)
        shortcut_2 = file_2.action_create_shortcut(False)
        shortcut_3 = file_3.action_create_shortcut(False)
        self.assertEqual(shortcut_1.access_internal, 'edit')
        self.assertEqual(shortcut_2.access_internal, 'view')
        self.assertEqual(shortcut_3.access_internal, 'none')

        # ** sanity check **
        # no write access, we should not update it
        self.assertEqual(file_2.with_user(self.internal_user).user_permission, 'view')
        self.assertEqual(shortcut_2.with_user(self.internal_user).user_permission, 'view')

        # we have write access on the target but not on the shortcut
        # (the shortcut should be updated in "SUDO" in order to keep them synchronized)
        self.assertEqual(file_3.with_user(self.internal_user).user_permission, 'edit')
        self.assertEqual(shortcut_3.with_user(self.internal_user).user_permission, 'none')
        # ******************

        root.with_user(self.internal_user).action_update_access_rights(access_via_link='view')

        self.assertEqual(root.access_via_link, 'view')
        self.assertEqual(file_1.access_via_link, 'view')
        self.assertEqual(file_2.access_via_link, 'none')
        self.assertEqual(file_3.access_via_link, 'view')
        self.assertEqual(shortcut_1.access_via_link, 'view')
        self.assertEqual(shortcut_2.access_via_link, 'none')
        self.assertEqual(shortcut_3.access_via_link, 'view')
        self.assertEqual(sub_folder.access_via_link, 'view')
        self.assertEqual(sub_file.access_via_link, 'view')

        # The access update is done only from the target to the shortcut,
        # and not from the shortcut to the target
        self.assertEqual(target.access_via_link, 'none')
        self.assertEqual(shortcut.access_via_link, 'none')

        # test the propagation of the members
        root.with_user(self.internal_user).action_update_access_rights(
            partners={self.internal_user.partner_id: ('edit', None)})

        def get_access(document):
            return document.access_ids.filtered(
                lambda a: a.partner_id == self.internal_user.partner_id).role

        self.assertEqual(get_access(root), 'edit')
        self.assertEqual(get_access(file_1), 'edit')
        self.assertEqual(get_access(file_2), False, 'The user can not write on that document')
        self.assertEqual(get_access(file_3), False)
        self.assertEqual(get_access(sub_folder), 'edit')
        self.assertEqual(get_access(sub_file), 'edit')

        # shortcut always synchronized
        self.assertEqual(get_access(shortcut_1), 'edit')
        self.assertEqual(get_access(shortcut_2), False)
        self.assertEqual(get_access(shortcut_3), False)

        # The members update is done only from the target to the shortcut,
        # and not from the shortcut to the target
        self.assertEqual(get_access(target), False)
        self.assertEqual(get_access(shortcut), False)

    def test_shortcuts_cant_have_children(self):
        folder_a_shortcut = self.folder_a.action_create_shortcut()
        with self.assertRaises(ValidationError):
            self.env['documents.document'].create({'type': 'folder', 'folder_id': folder_a_shortcut.id})
        self.folder_b.folder_id = folder_a_shortcut
        self.assertEqual(self.folder_b.folder_id, self.folder_a, "The shortcut's target should have been used")

    def test_portal_cant_own_root_documents(self):
        self.assertFalse(self.folder_a.folder_id)
        with self.assertRaises(UserError):
            self.folder_a.owner_id = self.portal_user

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_copy_document_access(self):
        """ Test that the copy method of document also copy access right. """
        IN_ONE_DAY = fields.Datetime.now() + datetime.timedelta(days=1)
        documents = self.document_gif | self.document_txt

        self.folder_b.access_internal = 'none'
        self.folder_b.action_update_access_rights(partners={self.internal_user.partner_id: ('view', False)})
        with self.assertRaises(AccessError, msg='No "edit" permission on the parent folder'):
            documents.with_user(self.internal_user).copy()

        self.folder_b.action_update_access_rights(partners={self.internal_user.partner_id: ('edit', False)})
        self.document_gif.action_update_access_rights(partners={self.internal_user.partner_id: (False, False)})
        self.document_gif.access_internal = 'none'
        with self.assertRaises(AccessError, msg='No access to one of the document'):
            documents.with_user(self.internal_user).copy()

        self.document_txt.action_update_access_rights(partners={self.portal_user.partner_id: ('view', IN_ONE_DAY)})
        self.document_gif.action_update_access_rights(partners={self.internal_user.partner_id: ('view', False)})
        # Copying folders is also possible
        (documents | self.folder_b).with_user(self.internal_user).copy()

        gif_copy, txt_copy = documents.with_user(self.internal_user).copy()
        self.assertTrue(gif_copy.attachment_id)
        gif_copy_access_ids = gif_copy.access_ids
        self.assertEqual(gif_copy_access_ids.partner_id, self.internal_user.partner_id)
        self.assertEqual(gif_copy_access_ids.role, 'view')
        self.assertFalse(gif_copy_access_ids.expiration_date)
        txt_copy_access_by_partner = {a.partner_id: (a.role, a.expiration_date) for a in txt_copy.access_ids}
        self.assertEqual(len(txt_copy_access_by_partner), 2)
        self.assertEqual(txt_copy_access_by_partner.get(self.portal_user.partner_id), ('view', IN_ONE_DAY))
        self.assertEqual(txt_copy_access_by_partner.get(self.internal_user.partner_id), ('edit', False))

        self.document_txt.action_archive()
        with self.assertRaises(UserError, msg='Cannot copy document in the Trash'):
            documents.with_user(self.internal_user).copy()

        url_document_in_my_folder = self.env['documents.document'].create(
            {'name': 'url', 'type': 'url', 'url': 'https://www.odoo.com/', 'owner_id': self.internal_user.id})
        _, url_copied = (self.document_gif | url_document_in_my_folder).copy()
        self.assertEqual(url_copied.owner_id, self.internal_user)

        shortcut = self.env['documents.document'].create(
            {'name': 'shortcut', 'shortcut_document_id': self.document_gif.id, 'owner_id': self.internal_user.id})

        # Copying shortcuts is also supported
        (url_document_in_my_folder | shortcut).copy()

    def test_updating_owner(self):
        self.assertEqual(self.folder_a_a.owner_id, self.doc_user)
        self.folder_a.action_update_access_rights(access_internal='edit')
        self.assertEqual(self.folder_a_a.with_user(self.internal_user).user_permission, 'edit')

        with self.assertRaises(AccessError):
            self.folder_a_a.with_user(self.internal_user).owner_id = self.internal_user

        self.folder_a_a.with_user(self.doc_user).owner_id = self.internal_user

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_embedded_action(self):
        """Test embedding and running actions on the right records"""
        self.folder_a.action_update_access_rights(
            access_internal="edit",
            partners={self.portal_user.partner_id: ('edit', False)}
        )
        server_action = self.env.ref('documents.ir_actions_server_tag_add_validated')
        with self.assertRaises(AccessError):
            self.env['documents.document'].with_user(self.internal_user).action_folder_embed_action(
                self.folder_a.id, server_action.id)
        self.env['documents.document'].with_user(self.doc_user).action_folder_embed_action(
            self.folder_a.id, server_action.id)
        doc = self.env['documents.document'].create({'name': 'A request', 'folder_id': self.folder_a.id})
        embedded_action = doc.available_embedded_actions_ids
        self.assertEqual(len(embedded_action), 1)
        doc_in_context = self.env['documents.document'].with_context(
            active_model='documents.document', active_id=doc.id)

        with self.assertRaises(AccessError):
            doc_in_context.with_user(self.portal_user).action_execute_embedded_action(embedded_action.id)
        doc_in_context.with_user(self.internal_user).action_execute_embedded_action(embedded_action.id)

        with self.assertRaises(UserError):
            doc_in_context.with_context(
                active_ids=(doc | self.folder_a).ids,
            ).with_user(self.internal_user).action_execute_embedded_action(embedded_action.id)
        doc.action_update_access_rights(access_internal='none')

        with self.assertRaises(AccessError):
            doc_in_context.with_context(
                active_id=doc.id
            ).with_user(self.internal_user).action_execute_embedded_action(embedded_action.id)

    def test_groupless_embedded_action_availability(self):
        """ Ensure that an embedded action which should otherwise be visible to a given document
        record remains visible in the case where it has `groups_ids=[]`.
        """
        embedded_action = self.env['ir.embedded.actions'].create({
            'name': 'public action',
            'parent_action_id': self.env.ref('documents.document_action').id,
            'action_id': self.env['ir.actions.actions'].search([
                ('type', '=', 'ir.actions.server'),
            ], limit=1).id,
            'parent_res_model': 'documents.document',
            'groups_ids': [Command.clear()],
            'parent_res_id': self.document_txt.folder_id.id,
        })
        self.assertIn(embedded_action, self.document_txt.available_embedded_actions_ids)
