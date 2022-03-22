# -*- coding: utf-8 -*-
# Odoo import
from odoo import fields, models
from ast import literal_eval


class StockMove(models.Model):
    _inherit = 'stock.move'

    created_sale_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string="Sale order line"
    )


class StockLocation(models.Model):
    _inherit = 'stock.location'

    warehouse_id_stored = fields.Many2one(
        'stock.warehouse',
        string='WH',
        related="warehouse_id",
        store=True
    )


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def _get_action(self, action_xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.display_name
        if self.code == 'internal':
            default_immediate_tranfer = False
        else:
            default_immediate_tranfer = True

        if self.env['ir.config_parameter'].sudo().get_param('stock.no_default_immediate_tranfer'):
            default_immediate_tranfer = False

        context = {
            'search_default_picking_type_id': [self.id],
            'default_picking_type_id': self.id,
            'default_immediate_transfer': default_immediate_tranfer,
            'default_company_id': self.company_id.id,
        }

        action_context = literal_eval(action['context'])
        context = {**action_context, **context}
        action['context'] = context
        return action
