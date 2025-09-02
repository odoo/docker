# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account_saft.tests.common import TestSaftReport
from odoo.tests import tagged

from freezegun import freeze_time
from itertools import starmap


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLuSaftReport(TestSaftReport):

    @classmethod
    @TestSaftReport.setup_country('lu')
    def setUpClass(cls):
        super().setUpClass()

        (cls.partner_a + cls.partner_b).write({
            'city': 'Garnich',
            'zip': 'L-8353',
            'country_id': cls.env.ref('base.lu').id,
            'phone': '+352 24 11 11 11',
        })

        cls.company_data['company'].write({
            'city': 'Garnich',
            'zip': 'L-8353',
            'company_registry': '123456',
            'phone': '+352 11 11 11 11',
            'country_id': cls.env.ref('base.lu').id,
        })

        cls.env['res.partner'].create({
            'name': 'Mr Big CEO',
            'is_company': False,
            'phone': '+352 24 11 12 34',
            'parent_id': cls.company_data['company'].partner_id.id,
        })

        cls.product_a.default_code = 'PA'
        cls.product_b.default_code = 'PB'
        cls.product_c = cls._create_product(name='product_c', lst_price=1000.0, standard_price=800.0, default_code='PA')
        cls.product_d = cls._create_product(name='product_d', lst_price=1000.0, standard_price=800.0, default_code=False)

        # Create invoices
        invoices = cls.env['account.move'].create(
            list(starmap(cls._l10n_lu_saft_invoice_data, [
                ('out_invoice', '2019-01-01', cls.partner_a, cls.product_a, 5.0, 1000.0),
                ('out_refund', '2019-03-01', cls.partner_a, cls.product_a, 3.0, 1000.0),
                ('in_invoice', '2018-12-31', cls.partner_b, cls.product_b, 10.0, 800.0),
            ])))
        invoices.action_post()

    @classmethod
    def _l10n_lu_saft_invoice_data(cls, move_type, invoice_date, partner, product, quantity, price_unit):
        tax_type = 'purchase' if move_type == 'in_invoice' else 'sale'
        return {
            'move_type': move_type,
            'invoice_date': invoice_date,
            'date': invoice_date,
            'partner_id': partner.id,
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
                'quantity': quantity,
                'price_unit': price_unit,
                'tax_ids': [Command.set(cls.company_data[f"default_tax_{tax_type}"].ids)]
            })]
        }

    def _l10n_lu_saft_generate_report(self, date_from='2019-01-01', date_to='2019-12-31'):
        options = self._generate_options(date_from, date_to)
        with freeze_time('2019-12-31'):
            return self.report_handler.l10n_lu_export_saft_to_xml(options)['file_content']

    def test_saft_report_errors(self):
        invoice_data = list(starmap(self._l10n_lu_saft_invoice_data, [
            ('out_invoice', '2019-01-01', self.partner_a, self.product_c, 5.0, 1000.0),
            ('out_invoice', '2019-01-01', self.partner_a, self.product_d, 5.0, 1000.0),
        ]))
        new_invoices = self.env['account.move'].create(invoice_data)
        new_invoices.action_post()
        with self.assertRaises(self.ReportException) as cm:
            self._l10n_lu_saft_generate_report()
        self.assertEqual(set(cm.exception.errors), {'product_duplicate_ref', 'product_missing_ref'})

    def test_saft_report_values(self):
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(self._l10n_lu_saft_generate_report()),
            self.get_xml_tree_from_string('''
                <AuditFile xmlns="urn:OECD:StandardAuditFile-Taxation/2.00">
                    <Header>
                        <AuditFileVersion>2.01</AuditFileVersion>
                        <AuditFileCountry>LU</AuditFileCountry>
                        <AuditFileDateCreated>2019-12-31</AuditFileDateCreated>
                        <SoftwareCompanyName>Odoo SA</SoftwareCompanyName>
                        <SoftwareID>Odoo</SoftwareID>
                        <SoftwareVersion>___ignore___</SoftwareVersion>
                        <Company>
                            <RegistrationNumber>123456</RegistrationNumber>
                            <Name>company_1_data</Name>
                            <Address>
                                <City>Garnich</City>
                                <PostalCode>L-8353</PostalCode>
                                <Country>LU</Country>
                            </Address>
                            <Contact>
                                <ContactPerson>
                                    <FirstName>NotUsed</FirstName>
                                    <LastName>Mr Big CEO</LastName>
                                </ContactPerson>
                                <Telephone>+352 24 11 12 34</Telephone>
                            </Contact>
                        </Company>
                        <DefaultCurrencyCode>EUR</DefaultCurrencyCode>
                        <SelectionCriteria>
                            <SelectionStartDate>2019-01-01</SelectionStartDate>
                            <SelectionEndDate>2019-12-31</SelectionEndDate>
                        </SelectionCriteria>
                        <TaxAccountingBasis>Invoice Accounting</TaxAccountingBasis>
                    </Header>
                    <MasterFiles>
                        <GeneralLedgerAccounts>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Result for the financial year</AccountDescription>
                                <StandardAccountID>142000</StandardAccountID>
                                <AccountType>Current Year Earni</AccountType>
                                <OpeningDebitBalance>8000.00</OpeningDebitBalance>
                                <ClosingDebitBalance>0.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Customers</AccountDescription>
                                <StandardAccountID>401100</StandardAccountID>
                                <AccountType>Receivable</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingDebitBalance>2340.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>VAT paid and recoverable</AccountDescription>
                                <StandardAccountID>421611</StandardAccountID>
                                <AccountType>Current Assets</AccountType>
                                <OpeningDebitBalance>1360.00</OpeningDebitBalance>
                                <ClosingDebitBalance>1360.00</ClosingDebitBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Suppliers (copy)</AccountDescription>
                                <StandardAccountID>441111</StandardAccountID>
                                <AccountType>Payable</AccountType>
                                <OpeningCreditBalance>9360.00</OpeningCreditBalance>
                                <ClosingCreditBalance>9360.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>VAT received</AccountDescription>
                                <StandardAccountID>461411</StandardAccountID>
                                <AccountType>Current Liabilitie</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>340.00</ClosingCreditBalance>
                            </Account>
                            <Account>
                                <AccountID>___ignore___</AccountID>
                                <AccountDescription>Sales of finished goods</AccountDescription>
                                <StandardAccountID>702100</StandardAccountID>
                                <AccountType>Income</AccountType>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingCreditBalance>2000.00</ClosingCreditBalance>
                            </Account>
                        </GeneralLedgerAccounts>
                        <Customers>
                            <Customer>
                                <Name>partner_a</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>partner_a</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 11 11</Telephone>
                                </Contact>
                                <CustomerID>___ignore___</CustomerID>
                                <OpeningDebitBalance>0.00</OpeningDebitBalance>
                                <ClosingDebitBalance>2340.00</ClosingDebitBalance>
                            </Customer>
                        </Customers>
                        <TaxTable>
                            <TaxTableEntry>
                                <TaxType>___ignore___</TaxType>
                                <Description>Taxe sur la valeur ajoutée</Description>
                                <TaxCodeDetails>
                                    <TaxCode>___ignore___</TaxCode>
                                    <Description>17% S</Description>
                                    <TaxPercentage>17.0</TaxPercentage>
                                    <Country>LU</Country>
                                </TaxCodeDetails>
                            </TaxTableEntry>
                        </TaxTable>
                        <UOMTable>
                            <UOMTableEntry>
                                <UnitOfMeasure>Units</UnitOfMeasure>
                                <Description>Unit</Description>
                            </UOMTableEntry>
                        </UOMTable>
                        <Products>
                            <Product>
                                <ProductCode>PA</ProductCode>
                                <ProductGroup>Test Category</ProductGroup>
                                <Description>product_a</Description>
                                <UOMBase>Units</UOMBase>
                            </Product>
                        </Products>
                        <Owners>
                            <Owner>
                                <RegistrationNumber>123456</RegistrationNumber>
                                <Name>company_1_data</Name>
                                <Address>
                                    <City>Garnich</City>
                                    <PostalCode>L-8353</PostalCode>
                                    <Country>LU</Country>
                                </Address>
                                <Contact>
                                    <ContactPerson>
                                        <FirstName>NotUsed</FirstName>
                                        <LastName>Mr Big CEO</LastName>
                                    </ContactPerson>
                                    <Telephone>+352 24 11 12 34</Telephone>
                                </Contact>
                                <OwnerID>___ignore___</OwnerID>
                            </Owner>
                        </Owners>
                    </MasterFiles>
                    <GeneralLedgerEntries>
                        <NumberOfEntries>2</NumberOfEntries>
                        <TotalDebit>9360.00</TotalDebit>
                        <TotalCredit>9360.00</TotalCredit>
                        <Journal>
                            <JournalID>___ignore___</JournalID>
                            <Description>Customer Invoices</Description>
                            <Type>sale</Type>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>01</Period>
                                <PeriodYear>2019</PeriodYear>
                                <TransactionDate>2019-01-01</TransactionDate>
                                <TransactionType>out_invoi</TransactionType>
                                <Description>INV/2019/00001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2019-01-01</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <CreditAmount>
                                        <Amount>5000.00</Amount>
                                    </CreditAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>850.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>17% S</Description>
                                    <CreditAmount>
                                        <Amount>850.00</Amount>
                                    </CreditAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-01-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>INV/2019/00001</Description>
                                    <DebitAmount>
                                        <Amount>5850.00</Amount>
                                    </DebitAmount>
                                </Line>
                            </Transaction>
                            <Transaction>
                                <TransactionID>___ignore___</TransactionID>
                                <Period>03</Period>
                                <PeriodYear>2019</PeriodYear>
                                <TransactionDate>2019-03-01</TransactionDate>
                                <TransactionType>out_refun</TransactionType>
                                <Description>RINV/2019/00001</Description>
                                <SystemEntryDate>___ignore___</SystemEntryDate>
                                <GLPostingDate>2019-03-01</GLPostingDate>
                                <CustomerID>___ignore___</CustomerID>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-03-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>[PA] product_a</Description>
                                    <DebitAmount>
                                        <Amount>3000.00</Amount>
                                    </DebitAmount>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>510.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-03-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>17% S</Description>
                                    <DebitAmount>
                                        <Amount>510.00</Amount>
                                    </DebitAmount>
                                </Line>
                                <Line>
                                    <RecordID>___ignore___</RecordID>
                                    <AccountID>___ignore___</AccountID>
                                    <ValueDate>2019-03-01</ValueDate>
                                    <SourceDocumentID>___ignore___</SourceDocumentID>
                                    <CustomerID>___ignore___</CustomerID>
                                    <Description>RINV/2019/00001</Description>
                                    <CreditAmount>
                                        <Amount>3510.00</Amount>
                                    </CreditAmount>
                                </Line>
                            </Transaction>
                        </Journal>
                    </GeneralLedgerEntries>
                    <SourceDocuments>
                        <SalesInvoices>
                            <NumberOfEntries>2</NumberOfEntries>
                            <TotalDebit>3000.00</TotalDebit>
                            <TotalCredit>5000.00</TotalCredit>
                            <Invoice>
                                <InvoiceNo>INV/2019/00001</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <Period>01</Period>
                                <PeriodYear>2019</PeriodYear>
                                <InvoiceDate>2019-01-01</InvoiceDate>
                                <InvoiceType>out_invoi</InvoiceType>
                                <GLPostingDate>2019-01-01</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>INV/2019/00001</OriginatingON>
                                        <OrderDate>2019-01-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>5.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>1000.00</UnitPrice>
                                    <TaxPointDate>2019-01-01</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>5000.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>C</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>850.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>850.00</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>5000.00</NetTotal>
                                    <GrossTotal>5850.00</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                            <Invoice>
                                <InvoiceNo>RINV/2019/00001</InvoiceNo>
                                <CustomerInfo>
                                    <CustomerID>___ignore___</CustomerID>
                                    <BillingAddress>
                                        <City>Garnich</City>
                                        <PostalCode>L-8353</PostalCode>
                                        <Country>LU</Country>
                                    </BillingAddress>
                                </CustomerInfo>
                                <Period>03</Period>
                                <PeriodYear>2019</PeriodYear>
                                <InvoiceDate>2019-03-01</InvoiceDate>
                                <InvoiceType>out_refun</InvoiceType>
                                <GLPostingDate>2019-03-01</GLPostingDate>
                                <TransactionID>___ignore___</TransactionID>
                                <Line>
                                    <AccountID>___ignore___</AccountID>
                                    <OrderReferences>
                                        <OriginatingON>RINV/2019/00001</OriginatingON>
                                        <OrderDate>2019-03-01</OrderDate>
                                    </OrderReferences>
                                    <ProductCode>PA</ProductCode>
                                    <ProductDescription>[PA] product_a</ProductDescription>
                                    <Quantity>3.0</Quantity>
                                    <InvoiceUOM>Units</InvoiceUOM>
                                    <UnitPrice>1000.00</UnitPrice>
                                    <TaxPointDate>2019-03-01</TaxPointDate>
                                    <Description>[PA] product_a</Description>
                                    <InvoiceLineAmount>
                                        <Amount>3000.00</Amount>
                                    </InvoiceLineAmount>
                                    <DebitCreditIndicator>D</DebitCreditIndicator>
                                    <TaxInformation>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>510.00</Amount>
                                        </TaxAmount>
                                    </TaxInformation>
                                </Line>
                                <DocumentTotals>
                                    <TaxInformationTotals>
                                        <TaxType>___ignore___</TaxType>
                                        <TaxCode>___ignore___</TaxCode>
                                        <TaxPercentage>17.0</TaxPercentage>
                                        <TaxBaseDescription>17% S</TaxBaseDescription>
                                        <TaxAmount>
                                            <Amount>510.00</Amount>
                                        </TaxAmount>
                                    </TaxInformationTotals>
                                    <NetTotal>-3000.00</NetTotal>
                                    <GrossTotal>-3510.00</GrossTotal>
                                </DocumentTotals>
                            </Invoice>
                        </SalesInvoices>
                    </SourceDocuments>
                </AuditFile>
            '''),
        )
