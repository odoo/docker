from odoo import models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payment_vals_from_batch(self, batch_result):
        # OVERRIDE
        # Ensure a bank account is set on all journal entries when attempting to pay using iso20022.
        self.ensure_one()
        lines = batch_result['lines']

        moves_wo_partner_bank = lines.move_id.filtered(lambda move: not move.partner_bank_id)
        if (self.payment_method_line_id.code in ['sepa_ct', 'iso20022', 'iso20022_se', 'iso20022_ch']
                and moves_wo_partner_bank
                and not lines.partner_id.commercial_partner_id.bank_ids):
            joined_moves_wo_partner_bnk = ', '.join(moves_wo_partner_bank.mapped('name'))
            raise UserError(_('A bank account must be set on the following documents: %s(doc_name)',
                              doc_name=joined_moves_wo_partner_bnk))
        return super()._create_payment_vals_from_batch(batch_result)
