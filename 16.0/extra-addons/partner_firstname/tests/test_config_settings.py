# Copyright 2015 Antiun Ingenieria S.L. - Antonio Espinosa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestConfigSettings(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["res.config.settings"].create({})

    def _change_partner_names_order(self):
        orders = [o[0] for o in self.config._partner_names_order_selection()]
        current = new = self.config.partner_names_order
        for o in orders:
            if o != current:
                new = o
                break
        self.config.partner_names_order = new

    def test_partner_names_order_changed(self):
        # The partner_names_order_changed is set to true at save time when
        # the value of partner_names_order is updated
        self.assertFalse(self.config.partner_names_order_changed)
        self._change_partner_names_order()
        self.assertTrue(self.config.partner_names_order_changed)

    def test_partner_names_order_changed_reset(self):
        # The partner_names_order_changed is reset to false when
        # the action action_recalculate_partners_name is executed
        self._change_partner_names_order()
        self.assertTrue(self.config.partner_names_order_changed)
        self.config.action_recalculate_partners_name()
        self.assertFalse(self.config.partner_names_order_changed)
