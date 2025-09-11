# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    exclude_provision_currency_ids = fields.Many2many('res.currency', relation='account_account_exclude_res_currency_provision', help="Whether or not we have to make provisions for the selected foreign currencies.")
    budget_item_ids = fields.One2many(comodel_name='account.report.budget.item', inverse_name='account_id')  # To use it in the domain when adding accounts from the report
