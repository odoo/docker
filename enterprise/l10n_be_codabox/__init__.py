from . import models
from . import wizard

from odoo.exceptions import UserError


def _l10n_be_codabox_pre_init_hook(env):
    valid_companies = env['res.company'].search([
        ('partner_id.country_id.code', '=', 'BE'),
        ('account_representative_id.vat', '!=', False),
        ('vat', '!=', False),
    ])
    if valid_companies:
        return

    if not env['ir.module.module'].search_count([('demo', '=', True)]):
        raise UserError(env._("The CodaBox module must be installed and configured by an Accounting Firm."))

    accounting_firm = env['res.partner'].create({
        'name': 'Demo Accounting Firm',
        'vat': 'BE0428759497',
        'country_id': env.ref('base.be').id,
    })
    env['res.company'].search([
        ('partner_id.country_id.code', '=', 'BE'),
        ('vat', '!=', False),
        '|',
            ('account_representative_id', '=', False),
            ('account_representative_id.vat', '=', False),
    ]).write({
        'account_representative_id': accounting_firm.id,
    })
