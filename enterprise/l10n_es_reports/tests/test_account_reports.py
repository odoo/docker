from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountReportsModelo(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].country_id = cls.env.ref('base.be').id
        cls.company_data['company'].currency_id = cls.env.ref('base.EUR').id
        cls.company_data['currency'] = cls.env.ref('base.EUR')

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Bidule',
            'company_id': cls.company_data['company'].id,
            'company_type': 'company',
            'country_id': cls.company_data['company'].country_id.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': 'Crazy Product',
            'lst_price': 100.0
        })

        cls.account_income = cls.env['account.account'].create({
            'account_type': 'income',
            'name': 'Account Income',
            'code': '121020',
            'reconcile': True,
        })

        cls.report = cls.env.ref('l10n_es_reports.mod_349')

    def test_mod349_rectifications(self):
        """
            Test the rectification part of modelo 349, if an in_refund/ot_refund is found in the period :
                - if the linked original invoice is in the same period or if there is no linked invoice -> "Invoices" section
                - if the linked original invoice is before the period -> "Refunds" section
        """
        options = self._generate_options(self.report, '2019-04-01', '2019-04-30')

        # 1) we create a move in april 2019
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) The move is not reversed yet, so it should appear in the "Invoices" section on the April 2019 report
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                         1],
            [
                ('Summary',                                                                                                                            ''),
                ('Total number of intra-community operations',                                                                                          1),
                ('Total amount of intra-community operations',                                                                                        400),
                ('Total number of intra-community refund operations',                                                                                   0),
                ('Amount of intra-community refund operations',                                                                                         0),
                ('Invoices',                                                                                                                           ''),
                ('E. Intra-community sales',                                                                                                          400),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                       0),
                ('D. Returns of goods previously sent from the TAI',                                                                                    0),
                ('C. Replacements of goods',                                                                                                            0),
                ('Refunds',                                                                                                                            ''),
                ('E. Intra-community sales refunds',                                                                                                    0),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                      0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                    0),
                ('C. Rectifications for replacement of goods',                                                                                          0),
            ],
            options
        )

        # 3) We reverse the move in May 2019
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'date': fields.Date.from_string('2019-05-05'),
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        reversal = move_reversal.reverse_moves()
        reversed_move = self.env['account.move'].browse(reversal['res_id'])
        # As we don't want to fully reverse the move, we only reverse 1 of the 4 products on the invoice_line
        reversed_move.invoice_line_ids.quantity = 1

        reversed_move.action_post()

        # 4) We change the report period to May 2019, as the rectifications must target a move in a previous period
        options = self._generate_options(self.report, '2019-05-01', '2019-05-31')

        # 5) Now, in the report of May 2019, the new balance of the move created in April 2019 is reported in the 'Refunds' section
        # The new balance is computed like this : invoice.residual_amount - reversed_move.amount_total
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                         1],
            [
                ('Summary',                                                                                                                            ''),
                ('Total number of intra-community operations',                                                                                          0),
                ('Total amount of intra-community operations',                                                                                          0),
                ('Total number of intra-community refund operations',                                                                                   1),
                ('Amount of intra-community refund operations',                                                                                    300.00),
                ('Invoices',                                                                                                                           ''),
                ('E. Intra-community sales',                                                                                                            0),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                       0),
                ('D. Returns of goods previously sent from the TAI',                                                                                    0),
                ('C. Replacements of goods',                                                                                                            0),
                ('Refunds',                                                                                                                            ''),
                ('E. Intra-community sales refunds',                                                                                               300.00),
                ('A. Intra-community purchases subject to taxes',                                                                                       0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                  0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                   0),
                ('I. Intra-community purchases of services',                                                                                            0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                            0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                              0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                      0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                    0),
                ('C. Rectifications for replacement of goods',                                                                                          0),
            ],
            options
        )

    def test_mod349_report_change_key_on_existing_move(self):
        """ This test makes sure the report display the lines depending on the key set on the move, even if we change
            the key of an existing move.
        """
        options = self._generate_options(self.report, fields.Date.from_string('2019-04-01'), fields.Date.from_string('2019-04-30'))

        # 1) We create an invoice with the key 'E'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        # 2) We make sure the report show the value in the 'E' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                   1],
            [
                ('Summary',                                                                                                                      ''),
                ('Total number of intra-community operations',                                                                                    1),
                ('Total amount of intra-community operations',                                                                               400.00),
                ('Total number of intra-community refund operations',                                                                             0),
                ('Amount of intra-community refund operations',                                                                                   0),
                ('Invoices',                                                                                                                     ''),
                ('E. Intra-community sales',                                                                                                 400.00),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                 0),
                ('D. Returns of goods previously sent from the TAI',                                                                              0),
                ('C. Replacements of goods',                                                                                                      0),
                ('Refunds',                                                                                                                      ''),
                ('E. Intra-community sales refunds',                                                                                              0),
                ('A. Intra-community purchases subject to taxes',                                                                                 0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                            0),
                ('S. Intra-community sales of services carried out by the declarant',                                                             0),
                ('I. Intra-community purchases of services',                                                                                      0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                      0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                        0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                              0),
                ('C. Rectifications for replacement of goods',                                                                                    0),
            ],
            options
        )

        # 3) We change the key of the invoice to set it to 'R'
        invoice.update({
            'state': 'draft',
            'l10n_es_reports_mod349_invoice_type': 'R',
        })
        invoice.action_post()

        # 4) The report should now put the value in the 'R' line
        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                             1],
            [
                ('Summary',                                                                                                                                ''),
                ('Total number of intra-community operations',                                                                                              1),
                ('Total amount of intra-community operations',                                                                                         400.00),
                ('Total number of intra-community refund operations',                                                                                       0),
                ('Amount of intra-community refund operations',                                                                                             0),
                ('Invoices',                                                                                                                               ''),
                ('E. Intra-community sales',                                                                                                                0),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                      400.00),
                ('D. Returns of goods previously sent from the TAI',                                                                                        0),
                ('C. Replacements of goods',                                                                                                                0),
                ('Refunds',                                                                                                                                ''),
                ('E. Intra-community sales refunds',                                                                                                        0),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                          0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                        0),
                ('C. Rectifications for replacement of goods',                                                                                              0),
            ],
            options
        )

    def test_mod349_credit_note(self):
        """
            Test the rectification part of modelo 349, if an refund is found without linked invoice
            it still ends up in the "Rectificaciones" section.
        """
        options = self._generate_options(self.report, fields.Date.from_string('2019-04-01'), fields.Date.from_string('2019-04-30'))

        invoice = self.env['account.move'].create({
            'move_type': 'out_refund',
            'date': fields.Date.from_string('2019-04-05'),
            'invoice_date': fields.Date.from_string('2019-04-05'),
            'partner_id': self.partner_a.id,
            'l10n_es_reports_mod349_invoice_type': 'E',
            'line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'account_id': self.account_income.id,
                    'quantity': 4,
                    'price_unit': self.product.lst_price,
                    'tax_ids': [],
                }),
            ]
        })

        invoice.action_post()

        self.assertLinesValues(
            self.report._get_lines(options),
            [0,                                                                                                                                                     1],
            [
                ('Summary',                                                                                                                                ''),
                ('Total number of intra-community operations',                                                                                              0),
                ('Total amount of intra-community operations',                                                                                              0),
                ('Total number of intra-community refund operations',                                                                                       1),
                ('Amount of intra-community refund operations',                                                                                        400.00),
                ('Invoices',                                                                                                                               ''),
                ('E. Intra-community sales',                                                                                                                0),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Transfers of goods made under consignment sales contracts.',                                                                           0),
                ('D. Returns of goods previously sent from the TAI',                                                                                        0),
                ('C. Replacements of goods',                                                                                                                0),
                ('Refunds',                                                                                                                                ''),
                ('E. Intra-community sales refunds',                                                                                                   400.00),
                ('A. Intra-community purchases subject to taxes',                                                                                           0),
                ('T. Sales to other member states exempted of intra-community taxes in case of triangular operations',                                      0),
                ('S. Intra-community sales of services carried out by the declarant',                                                                       0),
                ('I. Intra-community purchases of services',                                                                                                0),
                ('M. Intra-community sales of goods after an importation exempted of taxes',                                                                0),
                ('H. Intra-community sales of goods after an import exempted of taxes made for the fiscal representative',                                  0),
                ('R. Rectifications of transfers of goods made under consignment sale contracts.',                                                          0),
                ('D. Rectifications of returned goods previously sent from the TAI',                                                                        0),
                ('C. Rectifications for replacement of goods',                                                                                              0),
            ],
            options
        )
