from odoo import models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _get_currency_table_fiscal_year_bounds(self, main_company):
        # EXTENDS account
        default_bounds = super()._get_currency_table_fiscal_year_bounds(main_company)
        manual_fiscal_years = self.env['account.fiscal.year'].search(self.env['account.fiscal.year']._check_company_domain(main_company), order='date_from ASC')

        manual_bounds = manual_fiscal_years.mapped(lambda x: (x.date_from, x.date_to))
        rslt = []
        for default_from, default_to in default_bounds:
            while (
                manual_bounds
                and (
                    not default_to
                    or (default_from and default_from <= manual_bounds[0][0] and default_to >= manual_bounds[0][0])
                    or default_to >= manual_bounds[0][1]
                )):
                rslt.append(manual_bounds.pop(0))

            if not rslt or rslt[-1][1] < default_from:
                rslt.append((default_from, default_to))

        return rslt
