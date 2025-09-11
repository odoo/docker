# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # technical field used to reconcile the journal items in Odoo as they were in Winbooks
    winbooks_line_id = fields.Char(help="Line ID that was used in Winbooks")
