from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('state','picking_ids.state','picking_ids')
    def compute_order_status(self):
        for order in self:
            if order.state=='draft':
                order.order_state = 'draft'
            elif order.state=='sale':
                order.order_state = 'ready_to_pick'
                if order.picking_ids and order.picking_ids.filtered(lambda pick:pick.state=='confirmed'):
                    order.order_state = 'waiting'
                elif order.picking_ids and order.picking_ids.filtered(lambda pick:pick.backorder_id):
                    order.order_state = 'partial_ship'
                elif order.picking_ids and order.picking_ids.filtered(lambda pick:pick.state=='done'):
                        order.order_state = 'fully_ship'
                
            
    order_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('ready_to_pick', 'Ready to Pick'),
        ('partial_ship', 'Partially Shipped'),
        ('fully_ship', 'Fully Shipped'),
        ], string='Picking Status', compute='compute_order_status',store=True,readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')