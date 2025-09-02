from lxml import etree
from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def get_document_namespace(self, payment_method_code):
        if payment_method_code == 'iso20022_ch':
            return 'http://www.six-interbank-clearing.com/de/pain.001.001.03.ch.02.xsd'
        return super().get_document_namespace(payment_method_code)

    def _get_Dbtr(self, payment_method_code):
        Dbtr = super()._get_Dbtr(payment_method_code)
        if payment_method_code == 'iso20022_ch':
            result = list(filter(lambda x: x.tag != 'Id', Dbtr))
            new_dbtr = etree.Element('Dbtr')
            new_dbtr.extend(result)
            return new_dbtr
        return Dbtr
