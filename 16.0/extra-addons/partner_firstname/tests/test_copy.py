# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Test copy function for models."""
from odoo.tests.common import TransactionCase

from .base import MailInstalled


class UserCase(TransactionCase, MailInstalled):
    """Test ``res.users``."""

    def setUp(self):
        super(UserCase, self).setUp()
        self.create_original()
        self.create_original_multinames()

    def create_original(self):
        self.original = self.env["res.users"].create(
            {
                "firstname": "Firstname",
                "lastname": "Lastname",
                "name": "Firstname Lastname",
                "login": "firstname.lastname",
            }
        )

    def create_original_multinames(self):
        self.original_multinames = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "firstname": "Firstname1 Firstname2",
                    "lastname": "Lastname1 Lastname2",
                    "name": "Firstname1 Firstname2 Lastname1 Lastname2 (copy)",
                    "login": "firstname.multi",
                }
            )
        )

    def tearDown(self):
        super(UserCase, self).tearDown()

    def compare(self, copy):
        self.assertEqual(copy.lastname, "Lastname2")
        self.assertEqual(copy.firstname, "Firstname2")
        self.assertEqual(copy.name, "Firstname2 Lastname2")

    def test_copy_name(self):
        """Copy original with default name set - firstname lastname not set."""
        copy = self.original.copy({"name": "Firstname2 Lastname2"})
        self.compare(copy)

    def test_copy_firstname_lastname(self):
        """Copy original with default firstname and lastname set"""
        copy = self.original.copy({"firstname": "Firstname2", "lastname": "Lastname2"})
        self.compare(copy)

    def test_copy_firstname_lastname_name(self):
        """Copy original with default firstname, lastname and name set"""
        copy = self.original.copy(
            {
                "firstname": "Firstname2",
                "lastname": "Lastname2",
                "name": "Firstname2 Lastname2",
            }
        )
        self.compare(copy)

    def test_copy_multiple_names(self):
        copy = self.original_multinames.partner_id.copy()
        self.assertRecordValues(
            copy,
            [
                {
                    "firstname": "Firstname1 Firstname2",
                    "lastname": "Lastname1 Lastname2 (copy)",
                    "name": "Firstname1 Firstname2 Lastname1 Lastname2 (copy)",
                }
            ],
        )

    def test_copy_multiple_names_company(self):
        partner = self.original_multinames.partner_id
        partner.is_company = True
        copy = partner.copy()
        self.assertRecordValues(
            copy,
            [
                {
                    "firstname": False,
                    "lastname": "Firstname1 Firstname2 Lastname1 Lastname2 (copy)",
                    "name": "Firstname1 Firstname2 Lastname1 Lastname2 (copy)",
                }
            ],
        )
