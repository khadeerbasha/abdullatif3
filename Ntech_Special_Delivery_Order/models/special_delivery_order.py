# -*- coding: utf-8 -*-
from odoo import api, fields, models
import base64
from random import choice
from string import digits
import itertools
from werkzeug import url_encode
import pytz
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.modules.module import get_module_resource
from odoo.addons.resource.models.resource_mixin import timezone_datetime

import json
import time
from ast import literal_eval
from collections import defaultdict
from datetime import date
from itertools import groupby
from operator import itemgetter

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_datetime
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import format_date



class stock_picking(models.Model):
	_inherit = 'stock.picking'
    
	order_type = fields.Selection(related='picking_type_id.code')
	delivery_order_type = fields.Many2one('special.delivery.order', string="Delivery Order Type")
	
	
stock_picking()

class special_delivery_order(models.Model):
	_name = 'special.delivery.order'
	
	name = fields.Char(string="Name", required=True, help='Payment name')
	debit_account_id = fields.Many2one('account.account', string="Debit Account", required=True, help='Debit account for journal entry')
	credit_account_id = fields.Many2one('account.account', string="Credit Account", required=True, help='Credit account for journal entry')
	journal_id = fields.Many2one('account.journal', string="Journal", required=True, help='Journal for journal entry')


special_delivery_order()


class stock_move(models.Model):
	_inherit = 'stock.move'

	
	def  _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
		# This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
		spec_account = self.picking_id.delivery_order_type.name
		print ("SSSSSSSSSSSSSSSSSSSSSSSSSSSSS",spec_account)
		spec_deb_account = self.picking_id.delivery_order_type.debit_account_id.id
		print ("DDDDDDDDDDDDDDDDDDDDDDDDDDDD",spec_deb_account)
		spec_cred_account = self.picking_id.delivery_order_type.credit_account_id.id
		print ("cccccccccccccccccccccccccccc",spec_cred_account)
		self.ensure_one()
		if self.picking_id.delivery_order_type:
			centro = False 
			costo = False
			if self.location_id and self.location_id.usage == 'customer':  # goods returned from customer
				centro = self.analytic_account_id.id
			if self.location_id and self.location_id.usage == 'internal':
				costo = self.analytic_account_id.id
			#if self.picking_type_id.code == 'outgoing':
			debit_line_vals = {
				'name': description,
				'product_id': self.product_id.id,
				'quantity': qty,
				'product_uom_id': self.product_id.uom_id.id,
				'ref': description,
				'partner_id': partner_id,
				'debit': debit_value if debit_value > 0 else 0,
				'credit': -debit_value if debit_value < 0 else 0,
				'account_id': spec_deb_account,
				'analytic_account_id': costo or False,
			}
			credit_line_vals = {
				'name': description,
				'product_id': self.product_id.id,
				'quantity': qty,
				'product_uom_id': self.product_id.uom_id.id,
				'ref': description,
				'partner_id': partner_id,
				'credit': credit_value if credit_value > 0 else 0,
				'debit': -credit_value if credit_value < 0 else 0,
				'account_id': spec_cred_account,
				'analytic_account_id': centro or False,
			}
			#print ("RRRRRRRRRRRRRRRRRRRRRRRRR",debit_line_vals,credit_line_vals)			
		else:
			centro = False 
			costo = False
			if self.location_id and self.location_id.usage == 'customer':  # goods returned from customer
				centro = self.analytic_account_id.id
			if self.location_id and self.location_id.usage == 'internal':
				costo = self.analytic_account_id.id
			debit_line_vals = {
				'name': description,
				'product_id': self.product_id.id,
				'quantity': qty,
				'product_uom_id': self.product_id.uom_id.id,
				'ref': description,
				'partner_id': partner_id,
				'debit': debit_value if debit_value > 0 else 0,
				'credit': -debit_value if debit_value < 0 else 0,
				'account_id': debit_account_id,
				'analytic_account_id': costo or False,
			}
			credit_line_vals = {
				'name': description,
				'product_id': self.product_id.id,
				'quantity': qty,
				'product_uom_id': self.product_id.uom_id.id,
				'ref': description,
				'partner_id': partner_id,
				'credit': credit_value if credit_value > 0 else 0,
				'debit': -credit_value if credit_value < 0 else 0,
				'account_id': credit_account_id,
				'analytic_account_id': centro or False,
			}
			#print ("WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",debit_line_vals,credit_line_vals)
		rslt = {'credit_line_vals': credit_line_vals, 'debit_line_vals': debit_line_vals}
		#print ("QQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQ",rslt)
		if credit_value != debit_value:
			# for supplier returns of product in average costing method, in anglo saxon mode
			diff_amount = debit_value - credit_value
			price_diff_account = self.product_id.property_account_creditor_price_difference

			if not price_diff_account:
				price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
			if not price_diff_account:
				raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

			rslt['price_diff_line_vals'] = {
				'name': self.name,
				'product_id': self.product_id.id,
				'quantity': qty,
				'product_uom_id': self.product_id.uom_id.id,
				'ref': description,
				'partner_id': partner_id,
				'credit': diff_amount > 0 and diff_amount or 0,
				'debit': diff_amount < 0 and -diff_amount or 0,
				'account_id': price_diff_account.id,
			}
		return rslt


stock_move()

