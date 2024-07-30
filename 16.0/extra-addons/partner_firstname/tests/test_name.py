# Authors: Nemry Jonathan
# Copyright (c) 2014 Acsone SA/NV (http://www.acsone.eu)
# All Rights Reserved
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contact a Free Software
# Service Company.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

# Copyright 2024 Simone Rubino - Aion Tech
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

"""Test naming logic.

To have more accurate results, remove the ``mail`` module before testing.
"""

from .base import BaseCase


class PartnerContactCase(BaseCase):
    def test_update_lastname(self):
        """Change lastname."""
        self.expect("newlästname", self.firstname)
        self.original.name = self.name

    def test_update_firstname(self):
        """Change firstname."""
        self.expect(self.lastname, "newfïrstname")
        self.original.name = self.name

    def test_whitespace_cleanup(self):
        """Check that whitespace in name gets cleared."""
        self.expect("newlästname", "newfïrstname")
        self.original.name = "  newfïrstname  newlästname  "

        # Need this to refresh the ``name`` field
        self.original.invalidate_recordset(["name"])

    def test_multiple_name_creation(self):
        """Create multiple partners at once, only with "name"."""
        partners = self.env["res.partner"].create(
            [
                {
                    "name": "Test partner1",
                },
                {
                    "name": "Test partner2",
                },
            ]
        )
        self.assertRecordValues(
            partners,
            [
                {
                    "firstname": "Test",
                    "lastname": "partner1",
                },
                {
                    "firstname": "Test",
                    "lastname": "partner2",
                },
            ],
        )


class PartnerCompanyCase(BaseCase):
    def create_original(self):
        res = super(PartnerCompanyCase, self).create_original()
        self.original.is_company = True
        return res

    def test_copy(self):
        """Copy the partner and compare the result."""
        res = super(PartnerCompanyCase, self).test_copy()
        self.expect(self.name, False, self.name)
        return res

    def test_company_inverse(self):
        """Test the inverse method in a company record."""
        name = "Thïs is a Companŷ"
        self.expect(name, False, name)
        self.original.name = name


class UserCase(PartnerContactCase):
    def create_original(self):
        name = "{} {}".format(self.firstname, self.lastname)

        # Cannot create users if ``mail`` is installed
        if self.mail_installed():
            self.original = self.env.ref("base.user_demo")
            self.original.name = name
        else:
            self.original = self.env["res.users"].create(
                {"name": name, "login": "firstnametest@example.com"}
            )

    def test_copy(self):
        """Copy the partner and compare the result."""
        # Skip if ``mail`` is installed
        if not self.mail_installed():
            return super(UserCase, self).test_copy()
