from odoo.tools.float_utils import float_round

from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string="Warehouse",
        related="location_id.warehouse_id",
        store=True,
    )
    qty_available_sale = fields.Float(
        string='Quantity Available For Sales',
        compute='_compute_qty_available_sale',
    )

    @api.depends('product_id', 'quantity', 'location_id')
    def _compute_qty_available_sale(self):
        Move = self.env['stock.move']
        internal_move_domain = [
            ('state', '=', 'assigned'),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal')
        ]
        for quant in self:
            product = quant.product_id
            origin_product_id = product._origin.id
            product_id = product.id

            if not origin_product_id:
                quant.qty_available_sale = 0.0
                continue

            rounding = product.uom_id.rounding
            sub_domain = [
                ('product_id', '=', product_id),
                ('location_id', 'child_of', quant.location_id.id),
            ]
            internal_moves = Move.search(internal_move_domain + sub_domain)
            qty_internal_transfer = sum(internal_moves.mapped('reserved_availability'))
            quant.qty_available_sale = float_round(quant.available_quantity - qty_internal_transfer, precision_rounding=rounding)
