from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_nl_rounding_difference_loss_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_nl_rounding_difference_loss_account_id',
        readonly=False,
        string="Dutch VAT Rounding Loss Account",
        help="Account used for losses from rounding the lines of Dutch tax reports",
    )
    l10n_nl_rounding_difference_profit_account_id = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_nl_rounding_difference_profit_account_id',
        readonly=False,
        string="Dutch VAT Rounding Profit Account",
        help="Account used for profits from rounding the lines of Dutch tax reports",
    )
