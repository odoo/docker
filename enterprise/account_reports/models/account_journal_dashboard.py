from odoo import models

import ast


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_general_dashboard_data(self, dashboard_data):
        super()._fill_general_dashboard_data(dashboard_data)
        for journal in self.filtered(lambda journal: journal.type == 'general'):
            dashboard_data[journal.id]['is_account_tax_periodicity_journal'] = journal == journal.company_id._get_tax_closing_journal()

    def action_open_bank_balance_in_gl(self):
        ''' Show the bank balance inside the General Ledger report.
        :return: An action opening the General Ledger.
        '''
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_general_ledger")

        action['context'] = dict(ast.literal_eval(action['context']), default_filter_accounts=self.default_account_id.code)

        return action
