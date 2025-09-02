from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    missing_account_employees = fields.Many2many("hr.employee", string="Employees without Bank Account")

    def _reconcile_payments(self, to_process, edit_mode=False):
        super()._reconcile_payments(to_process, edit_mode=edit_mode)
        if self.env.context.get("hr_payroll_payment_register"):
            # Mark payslip as paid before superstream
            for vals in to_process:
                clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
                super_account = clearing_house.property_account_payable_id
                payslip = vals['to_reconcile'].move_id.payslip_ids
                if all(line.currency_id.is_zero(line.amount_residual_currency)
                    for line in payslip.move_id.line_ids.filtered(
                        lambda line: line.account_id != super_account
                    )
                ):
                    payslip.write(
                        {"state": "paid", "paid_date": self.payment_date}
                    )

        # Create a batche if payment register is created from hr.payslip.run
        if self.env.context.get("hr_payroll_payment_register_batch"):
            payments = self.env['account.payment'].concat(*[rec['payment'] for rec in to_process])
            payslip_batch = self.env['hr.payslip.run'].browse(self.env.context.get("hr_payroll_payment_register_batch"))

            if not payments:
                raise UserError(_("No payments to create a batch for."))

            payslip_batch.l10n_au_payment_batch_id = self.env['account.batch.payment'].create({
                'journal_id': payments[0].journal_id.id,
                'payment_ids': [(4, payment.id, None) for payment in payments],
                'payment_method_id': payments[0].payment_method_id.id,
                'batch_type': payments[0].payment_type,
                'name': f"Payroll Payments ({payslip_batch.name})",
                'l10n_au_is_payroll_payment': True,
            })

            payslip_batch.write({'state': 'paid'})

    def _create_payment_vals_from_batch(self, batch):
        res = super()._create_payment_vals_from_batch(batch)
        # Batch payment defaults to empoyee bank account
        if self.env.context.get("hr_payroll_payment_register_batch"):
            if "partner_bank_id" not in res:
                res['partner_bank_id'] = batch['lines'].move_id.payslip_ids.employee_id.bank_account_id.id
        return res

    def _compute_trust_values(self):
        super()._compute_trust_values()
        if self.env.context.get("hr_payroll_payment_register_batch"):
            self.missing_account_employees = self.line_ids.move_id.payslip_ids.employee_id\
                .filtered(lambda e: not e.sudo().bank_account_id)
            self.missing_account_partners = False

    def action_open_missing_account_employees(self):
        self.ensure_one()
        vals = {"name": _('Configure Employee Bank Account')}
        if len(self.missing_account_employees) > 1:
            vals['views'] = [
                (self.env.ref("l10n_au_hr_payroll_account.employee_missing_account_list_view").id, 'list'),
                (False, "form")
            ]
        return self.missing_account_employees._get_records_action(**vals)
