# Copyright 2015 Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""These tests try to mimic the behavior of the UI form.

The form operates in onchange mode, with its limitations.
"""

from odoo.tests.common import Form, TransactionCase

from ..exceptions import EmptyNamesError


class PartnerCompanyCase(TransactionCase):
    is_company = True

    def test_create_from_form(self):
        name = "Sôme company"
        with Form(self.env["res.partner"]) as partner_form:
            partner_form.company_type = "company" if self.is_company else "person"
            partner_form.name = name

        self.assertEqual(partner_form.name, name)
        self.assertEqual(partner_form.firstname, False)
        self.assertEqual(partner_form.lastname, name)

    def test_empty_name(self):
        """If we empty the name and save the form, EmptyNamesError must
        be raised (firstname and lastname are reset...)
        """
        with Form(
            self.env["res.partner"], view="base.view_partner_form"
        ) as partner_form:
            partner_form.company_type = "company" if self.is_company else "person"

            name = "Foó"
            # User sets a name
            partner_form.name = name
            # call save to  trigger the inverse
            partner_form.save()
            self.assertEqual(partner_form.name, name)
            self.assertEqual(partner_form.firstname, False)
            self.assertEqual(partner_form.lastname, name)

            # User unsets name
            partner_form.name = ""
            # call save to  trigger the inverse and therefore raise an exception
            with self.assertRaises(EmptyNamesError), self.env.cr.savepoint():
                partner_form.save()

            name += " bis"
            partner_form.name = name
            partner_form.save()
            self.assertEqual(partner_form.name, name)
            self.assertEqual(partner_form.firstname, False)

            # assert below will fail until merge of
            #   https://github.com/odoo/odoo/pull/45355
            # self.assertEqual(partner_form.lastname, name)


class PartnerContactCase(TransactionCase):
    is_company = False

    def test_create_from_form_only_firstname(self):
        """A user creates a contact with only the firstname from the form."""
        firstname = "Fïrst"
        with Form(self.env["res.partner"]) as partner_form:
            partner_form.company_type = "company" if self.is_company else "person"

            # Changes firstname, which triggers compute
            partner_form.firstname = firstname

        self.assertEqual(partner_form.lastname, False)
        self.assertEqual(partner_form.firstname, firstname)
        self.assertEqual(partner_form.name, firstname)

    def test_create_from_form_only_lastname(self):
        """A user creates a contact with only the lastname from the form."""
        lastname = "Läst"
        with Form(self.env["res.partner"]) as partner_form:
            partner_form.company_type = "company" if self.is_company else "person"

            # Changes lastname, which triggers compute
            partner_form.lastname = lastname

        self.assertEqual(partner_form.firstname, False)
        self.assertEqual(partner_form.lastname, lastname)
        self.assertEqual(partner_form.name, lastname)

    def test_create_from_form_all(self):
        """A user creates a contact with all names from the form."""
        firstname = "Fïrst"
        lastname = "Läst"
        with Form(self.env["res.partner"]) as partner_form:
            partner_form.company_type = "company" if self.is_company else "person"

            # Changes firstname, which triggers compute
            partner_form.firstname = firstname

            # Changes lastname, which triggers compute
            partner_form.lastname = lastname

        self.assertEqual(partner_form.lastname, lastname)
        self.assertEqual(partner_form.firstname, firstname)
        self.assertEqual(partner_form.name, " ".join((firstname, lastname)))
