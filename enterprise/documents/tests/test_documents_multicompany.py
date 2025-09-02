from odoo.addons.documents.tests.test_documents_common import TransactionCaseDocuments

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

MEMBER_VIEW, INTERNAL_VIEW, MEMBER_INTERNAL_VIEW, OWNER, MEMBER_VIEW_LINK_EDIT, INTERNAL_VIEW_LINK_EDIT = range(6)


class TestDocumentsMulticompany(TransactionCaseDocuments):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_allowed, cls.company_other, cls.company_disabled = cls.env['res.company'].create([
            {'name': f'Company {name}'} for name in ['Allowed', 'Other', 'Disabled']
        ])
        cls.admin_user = cls.env['res.users'].create({
            'email': "an_admin@yourcompany.com",
            'groups_id': [Command.link(cls.env.ref('documents.group_documents_system').id)],
            'login': "an_admin",
            'name': "An Admin",
        })
        (cls.internal_user + cls.document_manager + cls.portal_user + cls.admin_user).write({
            'company_ids': [Command.link(cls.company_allowed.id), Command.link(cls.company_disabled.id)],
        })

    def _make_test_documents(self, company_id, user):
        technical_root = self.env['documents.document'].sudo().create({
            'name': 'tech root', 'type': 'folder', 'access_internal': 'none', 'access_via_link': 'none',
            'company_id': self.company_other.id, 'owner_id': self.env.ref('base.user_root').id,
        })
        common = {
            'type': 'folder',
            'folder_id': technical_root.id,
            'access_internal': 'none',
            'access_via_link': 'none',
            'company_id': company_id
        }
        documents = (
            member_view, _internal_view, member_internal_view, _owner, member_view_link_edit,
            _internal_view_link_edit
        ) = (
            self.env['documents.document'].sudo().create([
                common | {'name': 'member view'},
                common | {'name': 'internal view', 'access_internal': 'view'},
                common | {'name': 'member + internal view', 'access_internal': 'view'},
                common | {'name': 'owner', 'owner_id': user.id},
                common | {'name': 'member view + link edit', 'access_via_link': 'edit'},
                common | {'name': 'internal view + link edit', 'access_internal': 'view', 'access_via_link': 'edit'}
            ])
        )
        self.env['documents.access'].sudo().create([
            {
                'document_id': document.id,
                'partner_id': user.partner_id.id,
                'role': 'view'
            } for document in (member_view, member_internal_view, member_view_link_edit)
        ])
        return documents.with_context({'allowed_company_ids': self.company_allowed.ids})

    @staticmethod
    def _assert_documents_equal(found, expected):
        message_items = []
        if extra := found - expected:
            message_items.append(f'Extra records found: {extra.mapped("name")}')
        if missing := expected - found:
            message_items.append(f'Missing records: {missing.mapped("name")}')
        if message_items:
            raise AssertionError(" - ".join(message_items))

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_company_access_simple(self):
        self.assertEqual(self.folder_b.access_internal, 'view')
        self.folder_b.company_id = self.company_allowed
        self.folder_b.with_user(self.internal_user).with_company(self.company_allowed).check_access('read')
        self._assert_raises_check_access_rule(
            self.folder_b.with_user(self.internal_user).with_company(self.company_other), 'read')

    def _test_company_with_user(self, cases, user):
        """Test access rights depending on access rights and company.

        :param list[tuple] cases: shaped as (company, expected_edit_indices, expected_view_indices) with:
            company: company used as documents company_id,
            expected_edit_indices: indices for documents with expected 'edit' permission,
            expected_view_indices: indices for documents with expected 'view' permission
        :param: user used as member or owner when creating documents and to test access for
        """
        for company, expected_edit_indices, expected_view_indices in cases:
            with self.subTest(company_name=company.name):
                Documents_with_ctx = self.env['documents.document'].with_user(user).with_context(
                    allowed_company_ids=self.company_allowed.ids
                )
                docs = self._make_test_documents(company.id, user)
                expected_view = Documents_with_ctx.browse(docs[idx].id for idx in expected_view_indices)
                expected_edit = Documents_with_ctx.browse(docs[idx].id for idx in expected_edit_indices)

                search_view = Documents_with_ctx.search([('id', 'in', docs.ids), ('user_permission', '=', 'view')])
                with self.subTest(permission='view'):
                    self._assert_documents_equal(search_view, expected_view)

                search_edit = Documents_with_ctx.search([('id', 'in', docs.ids), ('user_permission', '=', 'edit')])
                with self.subTest(permission='edit'):
                    self._assert_documents_equal(search_edit, expected_edit)

                expected_user_permissions = [
                    'view' if document in expected_view else 'edit' if document in expected_edit else 'none'
                    for document in docs
                ]
                user_permissions = docs.with_user(user).mapped('user_permission')
                self.assertListEqual(user_permissions, expected_user_permissions)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_company_access_admin(self):
        ALL_DOCUMENTS = list(range(6))
        cases = [
            (self.env['res.company'], ALL_DOCUMENTS, []),
            (self.company_allowed, ALL_DOCUMENTS, []),
            (self.company_other, ALL_DOCUMENTS, []),
            (self.company_disabled, [], []),
        ]
        self._test_company_with_user(cases, self.admin_user)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_company_access_manager(self):
        cases = [
            (self.env['res.company'],
             [INTERNAL_VIEW, MEMBER_INTERNAL_VIEW, OWNER, MEMBER_VIEW_LINK_EDIT, INTERNAL_VIEW_LINK_EDIT], [MEMBER_VIEW]),
            (self.company_allowed,
             [INTERNAL_VIEW, OWNER, MEMBER_INTERNAL_VIEW, MEMBER_VIEW_LINK_EDIT, INTERNAL_VIEW_LINK_EDIT], [MEMBER_VIEW]),
            (self.company_other, [OWNER, MEMBER_VIEW_LINK_EDIT], [MEMBER_VIEW, MEMBER_INTERNAL_VIEW]),
            (self.company_disabled, [], []),
        ]
        self._test_company_with_user(cases, self.document_manager)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_company_access_internal(self):
        cases = [
            (self.env['res.company'],
             [OWNER, MEMBER_VIEW_LINK_EDIT, INTERNAL_VIEW_LINK_EDIT], [MEMBER_VIEW, INTERNAL_VIEW, MEMBER_INTERNAL_VIEW]),
            (self.company_allowed,
             [OWNER, MEMBER_VIEW_LINK_EDIT, INTERNAL_VIEW_LINK_EDIT], [MEMBER_VIEW, INTERNAL_VIEW, MEMBER_INTERNAL_VIEW]),
            (self.company_other, [OWNER, MEMBER_VIEW_LINK_EDIT], [MEMBER_VIEW, MEMBER_INTERNAL_VIEW]),
            (self.company_disabled, [], []),
        ]
        self._test_company_with_user(cases, self.internal_user)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_company_access_portal(self):
        cases = [
            (self.env['res.company'], [OWNER, MEMBER_VIEW_LINK_EDIT], [MEMBER_VIEW, MEMBER_INTERNAL_VIEW]),
            (self.company_allowed, [OWNER, MEMBER_VIEW_LINK_EDIT], [MEMBER_VIEW, MEMBER_INTERNAL_VIEW]),
            (self.company_other, [OWNER, MEMBER_VIEW_LINK_EDIT], [MEMBER_VIEW, MEMBER_INTERNAL_VIEW]),
            (self.company_disabled, [], []),
        ]
        self._test_company_with_user(cases, self.portal_user)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_company_shortcut_mismatch(self):
        docs = self._make_test_documents(self.company_allowed.id, self.internal_user)
        member_view_link_edit = docs[4]
        Documents_with_ctx = self.env['documents.document'].with_user(self.internal_user).with_context(
            allowed_company_ids=self.company_allowed.ids
        )
        self.assertEqual(member_view_link_edit.user_permission, 'edit')
        shortcut = member_view_link_edit.action_create_shortcut(False)
        self.assertEqual(shortcut.company_id, self.company_allowed)
        member_view_link_edit.company_id = self.company_disabled
        self.assertFalse(Documents_with_ctx.search([('id', '=', shortcut.id)]))
        self.assertEqual(shortcut.user_permission, 'none')

        member_view_link_edit.company_id = self.company_allowed
        self.assertEqual(shortcut.company_id, self.company_allowed)

        with self.assertRaises(ValidationError):
            shortcut.sudo().company_id = self.company_disabled

        member_view_link_edit.company_id = False
        self.assertEqual(shortcut.company_id, self.company_allowed)
        self.assertEqual(Documents_with_ctx.search([('id', '=', shortcut.id)]), shortcut)
        self.assertEqual(shortcut.user_permission, 'edit')

    # todo: access via parent
