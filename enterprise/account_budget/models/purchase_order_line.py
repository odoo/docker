# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    analytic_json = fields.Json('Analytic JSON', compute='_compute_analytic_json', store=True)
    is_above_budget = fields.Boolean('Is Above Budget', compute='_compute_above_budget')
    budget_line_ids = fields.One2many('budget.line', compute='_compute_budget_line_ids', string='Budget Lines')

    @api.depends('analytic_distribution')
    def _compute_analytic_json(self):
        for line in self:
            distribution = []
            for analytic_account_ids, percentage in (line.analytic_distribution or {}).items():
                dist_dict = {'rate': float(percentage) / 100}
                for analytic_account in self.env['account.analytic.account'].browse(map(int, analytic_account_ids.split(","))).exists():
                    root_plan = analytic_account.root_plan_id
                    dist_dict[root_plan._column_name()] = analytic_account.id
                distribution.append(dist_dict)
            line.analytic_json = distribution

    @api.depends('analytic_distribution')
    def _compute_budget_line_ids(self):
        def get_domain(line):
            if line.analytic_json and line.product_qty - line.qty_received > 0:
                for json in line.analytic_json:
                    return tuple([
                        ('budget_analytic_id', 'any', (
                            ('budget_type', '!=', 'revenue'),
                            ('state', '=', 'confirmed'),
                        )),
                        ('date_from', '<=', line.order_id.date_order),
                        ('date_to', '>=', line.order_id.date_order),
                    ] + [
                        (key, '=', value)
                        for key, value in json.items()
                        if key in self.env['budget.line']._fields
                    ])

        for domain, lines in self.grouped(get_domain).items():
            lines.budget_line_ids = bool(domain) and self.sudo().env['budget.line'].search(list(domain))

    @api.depends('budget_line_ids', 'price_unit', 'product_qty', 'qty_invoiced')
    def _compute_above_budget(self):
        for line in self:
            uncommitted_amount = 0
            if line.order_id.state not in ('purchase', 'done'):
                uncommitted_amount = line.price_unit * (line.product_qty - line.qty_invoiced)
            line.is_above_budget = any(budget.committed_amount + uncommitted_amount > budget.budget_amount for budget in line.budget_line_ids)
