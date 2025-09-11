from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['pos.delivery.provider']
        return data

    def get_closing_control_data(self):
        data = super().get_closing_control_data()
        orders = self._get_closed_orders()
        urban_piper_payment_method_ids = self.config_id.urbanpiper_payment_methods_ids
        urban_piper_non_cash_payments_grouped_by_method_id = {pm: orders.payment_ids.filtered(lambda p: p.payment_method_id == pm) for pm in urban_piper_payment_method_ids}
        if data.get('non_cash_payment_methods'):
            non_cash_methods = [
                {
                    'name': pm.name,
                    'amount': sum(urban_piper_non_cash_payments_grouped_by_method_id[pm].mapped('amount')),
                    'number': len(urban_piper_non_cash_payments_grouped_by_method_id[pm]),
                    'id': pm.id,
                    'type': pm.type,
                }
                for pm in urban_piper_non_cash_payments_grouped_by_method_id
            ]
            data['non_cash_payment_methods'].extend(non_cash_methods)
        return data
