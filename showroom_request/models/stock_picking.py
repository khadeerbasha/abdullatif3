# -*- coding: utf-8 -*-

# Python imports

# Odoo Imports
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    showroom_request_id = fields.Many2one(
        comodel_name='showroom.request',
        string='Showroom Request',
        readonly=True,
    )
