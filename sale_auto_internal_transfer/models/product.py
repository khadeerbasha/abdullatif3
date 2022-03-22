# -*- coding: utf-8 -*-
# Odoo Imports
from odoo import fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_available_sale = fields.Float(
        string='Quantity Available For Sales',
        compute='_compute_quantities',
        search='_search_qty_available',
        digits='Product Unit of Measure',
        compute_sudo=False,
    )
    product_quant_ids = fields.Many2many(
        'stock.quant',
        string="Product stock by warehouse",
        compute="_compute_stock_by_warehouse"
    )

    def _compute_stock_by_warehouse(self):
        for product in self:
            product_quant_ids = self.env['stock.quant'].search(
                [('product_id', '=', product.id), ('location_id.usage', '=', 'internal')], ).filtered(
                lambda l: (l.quantity and l.qty_available_sale and l.available_quantity) > 0)
            product.product_quant_ids = product_quant_ids

    def _compute_quantities(self):
        super(ProductProduct, self)._compute_quantities()

        products = self.filtered(lambda p: p.type != 'service')
        res = products._compute_quantities_dict(
            self._context.get('lot_id'),
            self._context.get('owner_id'),
            self._context.get('package_id'),
            self._context.get('from_date'),
            self._context.get('to_date')
        )

        for product in products:
            product.qty_available_sale = res[product.id]['qty_available_sale']

        # Services need to be set with 0.0 for all qty_available_sale
        services = self - products
        services.qty_available_sale = 0.0

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super(ProductProduct, self)._compute_quantities_dict(lot_id, owner_id, package_id, from_date, to_date)
        Move = self.env['stock.move']
        internal_move_domain = [
            ('state', '=', 'assigned'),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal')
        ]
        for product in self:
            origin_product_id = product._origin.id
            product_id = product.id

            if not origin_product_id:
                res[product_id]['qty_available_sale'] = 0.0
                continue
            rounding = product.uom_id.rounding

            internal_moves = Move.search(internal_move_domain + [('product_id', '=', product_id)])
            qty_internal_transfer = sum(internal_moves.mapped('reserved_availability'))

            qty_available_sale = res[product_id]['qty_available'] - qty_internal_transfer
            res[product_id]['qty_available_sale'] = float_round(qty_available_sale, precision_rounding=rounding)
        return res

    def _get_qty_available_sale_location(self, location_id):
        qty_available_sale_location = 0.0
        Move = self.env['stock.move']
        stock_quant = self.env['stock.quant']
        internal_move_domain = [
            ('state', '=', 'assigned'),
            ('location_id', '=', location_id.id),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
        ]
        for product in self:
            product_id = product.id

            rounding = product.uom_id.rounding

            internal_moves = Move.search(internal_move_domain + [('product_id', '=', product_id)])
            qty_internal_transfer = sum(internal_moves.mapped('reserved_availability'))
            product_qty_available = stock_quant.sudo()._get_available_quantity(product_id=product,
                                                                               location_id=location_id,
                                                                               lot_id=None,
                                                                               package_id=None,
                                                                               owner_id=None,
                                                                               strict=False)
            qty = product_qty_available - qty_internal_transfer
            qty_available_sale_location = float_round(qty, precision_rounding=rounding)
        return qty_available_sale_location


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    qty_available_sale = fields.Float(
        string='Quantity Available For Sales',
        compute='_compute_quantities',
        search='_search_qty_available',
        compute_sudo=False,
        digits='Product Unit of Measure'
    )
    product_quant_ids = fields.Many2many(
        'stock.quant',
        string="Product stock by warehouse",
        compute="_compute_stock_by_warehouse"
    )

    def _compute_stock_by_warehouse(self):
        for product in self:
            product_quant_ids = self.env['stock.quant'].search(
                [('product_tmpl_id', '=', product.id),
                 ('location_id.usage', '=', 'internal')]).filtered(
                lambda l: (l.quantity and l.qty_available_sale and l.available_quantity) > 0)
            product.product_quant_ids = product_quant_ids

    def _compute_quantities(self):
        super(ProductTemplate, self)._compute_quantities()
        res = self._compute_quantities_dict()
        for template in self:
            template.qty_available_sale = res[template.id]['qty_available_sale']

    def _compute_quantities_dict(self):
        prod_available = super(ProductTemplate, self)._compute_quantities_dict()
        variants_available = {
            p['id']: p for p in self.product_variant_ids.read(['qty_available_sale'])
        }

        for template in self:
            qty_available_sale = 0

            for p in template.product_variant_ids:
                qty_available_sale += variants_available[p.id]["qty_available_sale"]

            prod_available[template.id].update({
                "qty_available_sale": qty_available_sale,
            })

        return prod_available
