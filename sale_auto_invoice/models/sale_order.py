# -*- coding: utf-8 -*-

# Odoo Imports
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fully_invoice = fields.Boolean(
        string='Can be fully invoiced',
        compute='_compute_fully_invoice',
        # store=True
    )

    @api.depends('order_line',
                 'order_line.is_fully_delivered',
                 'state',
                 'picking_ids'
                 )
    def _compute_fully_invoice(self):
        for order in self:
            order_line = order.order_line.filtered(lambda l: l.product_type == "product")
            if order.invoice_status == 'to invoice' and order.state in ('sale', 'done') and all(
                    line.product_id.type not in ('service', 'consu') and line.is_fully_delivered for line in
                    order_line):

                order.fully_invoice = True
            else:
                order.fully_invoice = False
            if order.invoice_status != 'invoiced' and order.fully_invoice:
                inv_id = self.sudo()._create_invoices(grouped=False, final=True)
                inv_id.sudo().action_post()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_fully_delivered = fields.Boolean(
        string="Is Fully delivered",
        compute='_compute_fully_delivered',
        store=True,
    )

    @api.depends('qty_delivered')
    def _compute_fully_delivered(self):
        for line in self:
            if line.product_type == 'product' and (line.qty_delivered >= line.product_uom_qty):
                line.is_fully_delivered = True
            else:
                line.is_fully_delivered = False
