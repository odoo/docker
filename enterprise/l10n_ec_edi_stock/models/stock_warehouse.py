from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    l10n_ec_entity = fields.Char(
        string="Entity Point",
        size=3,
        copy=False,
        help="Ecuador: Emission entity number that is given by the SRI."
    )
    l10n_ec_emission = fields.Char(
        string="Emission Point",
        size=3, copy=False,
        help="Ecuador: Emission point number that is given by the SRI."
    )
    l10n_ec_delivery_number = fields.Integer(
        string="Next Delivery Guide Number",
        copy=False,
        readonly=False,
        default=1,
        related='l10n_ec_delivery_number_sequence_id.number_next',
        help="Ecuador: Hold the next sequence to use as delivery guide number.",
    )
    l10n_ec_delivery_number_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Delivery Guide Number Sequence",
        compute='_compute_l10n_ec_delivery_number_sequence',
        store=True,
        precompute=True,
        help="Ecuador: Hold the sequence to generate a delivery guide number.",
    )
    l10n_ec_country_code = fields.Char(
        string="Country Code(EC)",
        related='company_id.country_code',
        depends=['company_id']
    )

    _sql_constraints = [(
        'unique_warehouse_ec_entity_and_emission', 'UNIQUE(l10n_ec_entity, l10n_ec_emission)',
        'Duplicated warehouse (entity, emission) pair. You probably encoded twice the same warehouse.'
    )]

    @api.depends('l10n_ec_entity', 'l10n_ec_emission')
    def _compute_l10n_ec_delivery_number_sequence(self):
        """
        Compute the sequence for the delivery guide number and
        check if the warehouse has the required fields to create the sequence
        """
        warehouses_to_process = self.filtered(
            lambda warehouse: warehouse.l10n_ec_entity and warehouse.l10n_ec_emission
            and not warehouse.l10n_ec_delivery_number_sequence_id
            and not isinstance(warehouse.id, models.NewId)
        )
        for warehouse in warehouses_to_process:
            warehouse.l10n_ec_delivery_number_sequence_id = warehouse._l10n_ec_create_delivery_guide_sequence()

    def _l10n_ec_create_delivery_guide_sequence(self):
        '''
        Create a sequence for the delivery guide number
        '''
        self.ensure_one()
        return self.env['ir.sequence'].sudo().create({
            'name': f"Stock Picking Delivery Guide Sequence for {self.name}",
            'code': f"l10n_ec_edi_stock.stock_picking_dgs_{self.id}",
            'padding': 9,
            'company_id': self.company_id.id,
            'number_next': 1,
            'implementation': 'no_gap',
        })
