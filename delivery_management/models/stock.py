# -*- coding: utf-8 -*-
# Odoo import
from odoo import fields, models, SUPERUSER_ID, api
from ast import literal_eval


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tracking_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirm'),
        ('reschedule', 'Reschedule'),
        ('waiting', 'Waiting'),
        ('done', 'done'),
        ('cancel', 'Canceled'),
    ],
        string="Tracking State",
        tracking=True,
        readonly=True,
        default='draft',
        group_expand='_expand_tracking_state'
    )

    @api.model
    def _expand_tracking_state(self, states, domain, order):
        return [key for key, val in type(self).tracking_state.selection]

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        self.tracking_state = 'waiting'
        return res

    def button_validate_delivery(self):
        self.ensure_one()
        self.tracking_state = 'done'
        return self.env.ref('delivery_management.act_window_delivery_management_dashboard').sudo().read()[0]

    def button_confirm_delivery(self):
        self.ensure_one()
        self.tracking_state = 'confirmed'
        return self.env.ref('delivery_management.act_window_delivery_management_dashboard').sudo().read()[0]
        # todo sms confirmation with OTP code confirmation

    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        self.tracking_state = 'cancel'
        return res

    def action_reschedule_delivery(self):
        return {
            'name': 'Reschedule Delivery',
            'res_model': 'reschedule.delivery.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_mode': 'form',

        }
