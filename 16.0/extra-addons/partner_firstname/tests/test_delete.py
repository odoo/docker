# Copyright 2015 Grupo ESOC
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase

from .base import MailInstalled


class CompanyCase(TransactionCase):
    model = "res.partner"
    context = {"default_is_company": True}

    def test_computing_after_unlink(self):
        """Test what happens if recomputed after unlinking.

        This test might seem useless, but really this happens when module
        ``partner_relations`` is installed.

        See https://github.com/OCA/partner-contact/issues/154.
        """
        data = {"name": "Söme name"}
        record = self.env[self.model].with_context(**self.context).create(data)
        record.unlink()
        record.flush_recordset()


class PersonCase(CompanyCase):
    context = {"default_is_company": False}


class UserCase(CompanyCase, MailInstalled):
    model = "res.users"
    context = {"default_login": "user@example.com"}

    def test_computing_after_unlink(self):
        # Cannot create users if ``mail`` is installed
        if not self.mail_installed():
            return super(UserCase, self).test_computing_after_unlink()
