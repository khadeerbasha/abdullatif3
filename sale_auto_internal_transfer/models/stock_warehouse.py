from odoo.tools.float_utils import float_round

from odoo import api, fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    wh_transit_loc_id = fields.Many2one(
        'stock.location',
        string="Transit location",
        readonly=True,
    )

    def _get_locations_values(self, vals, code=False):
        """ Update the warehouse locations. """
        def_values = self.default_get(['reception_steps', 'delivery_steps'])
        reception_steps = vals.get('reception_steps', def_values['reception_steps'])
        delivery_steps = vals.get('delivery_steps', def_values['delivery_steps'])
        code = vals.get('code') or code or ''
        code = code.replace(' ', '').upper()
        company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
        sub_locations = {
            'lot_stock_id': {
                'name': _('Stock'),
                'active': True,
                'usage': 'internal',
                'barcode': self._valid_barcode(code + '-STOCK', company_id)
            },
            'wh_input_stock_loc_id': {
                'name': _('Input'),
                'active': reception_steps != 'one_step',
                'usage': 'internal',
                'barcode': self._valid_barcode(code + '-INPUT', company_id)
            },
            'wh_qc_stock_loc_id': {
                'name': _('Quality Control'),
                'active': reception_steps == 'three_steps',
                'usage': 'internal',
                'barcode': self._valid_barcode(code + '-QUALITY', company_id)
            },
            'wh_output_stock_loc_id': {
                'name': _('Output'),
                'active': delivery_steps != 'ship_only',
                'usage': 'internal',
                'barcode': self._valid_barcode(code + '-OUTPUT', company_id)
            },
            'wh_transit_loc_id': {
                'name': _('Transit'),
                'active': True,
                'usage': 'transit',
                'barcode': self._valid_barcode(code + '-Transit', company_id)
            },
        }
        return sub_locations

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
            quant.qty_available_sale = float_round(quant.available_quantity - qty_internal_transfer,
                                                   precision_rounding=rounding)
