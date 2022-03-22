from odoo import api, fields, models, _


class WarehouseProductStock(models.TransientModel):
    _name = 'warehouse.product.stock'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    location_id = fields.Many2one('stock.location', string='Location')
    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string='Available Qty')
    available_qty_for_sale = fields.Float(string='Available Qty for Sale')
    available_qty_on_hand = fields.Float(string='On Hand Qty')
    warehouse_product_id = fields.Many2one('warehouse.product.wizard', string='Warehouse Products')
