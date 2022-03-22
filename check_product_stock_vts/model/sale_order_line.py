from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    def show_product_stock_wizard(self):
        ctx = {'product_id':self.product_id.id}        
        return {
            'name': "Warehouse Product Stock",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'warehouse.product.wizard',
            'type': 'ir.actions.act_window',
            'context':ctx,
            'target':'new',
            }