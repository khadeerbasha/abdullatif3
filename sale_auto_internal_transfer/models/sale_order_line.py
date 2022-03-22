# -*- coding: utf-8 -*-
# Python import
from dateutil.relativedelta import relativedelta

# Odoo Imports
from odoo.tools.float_utils import float_compare
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    internal_move_dest_ids = fields.One2many(
        comodel_name='stock.move',
        inverse_name='created_sale_line_id',
        string='Downstream Internal Moves'
    )
    warehouse_location_id = fields.Many2one(
        comodel_name='stock.location',
        string="Transfer From WH",
        domain="[('usage', '=', 'internal'),('warehouse_id_stored','!=',warehouse_id)]"
    )
    internal_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string="Internal Warehouse",
        compute='_compute_internal_warehouse'
    )
    is_available = fields.Boolean(
        string="Available",
        # compute='_compute_is_available',
        store=True,
        readonly=True,
        default=False,
        copy=False,
    )
    propagate_cancel = fields.Boolean(
        string='Propagate cancellation',
        default=True
    )

    # Compute Methods
    @api.depends('product_id', 'product_uom_qty', 'state')
    def _compute_is_available(self):
        for line in self:
            if line.state in ('sale', 'done', 'cancel'):
                line.is_available = True
            else:
                line.is_available = False

    @api.depends('route_id', 'warehouse_location_id', 'product_uom_qty')
    def _compute_internal_warehouse(self):
        for order_line in self:
            if order_line.warehouse_location_id:
                order_line.internal_warehouse_id = order_line.warehouse_location_id.warehouse_id
            else:
                order_line.internal_warehouse_id = False

    @api.onchange('product_id', 'product_uom_qty', 'product_uom', 'warehouse_location_id', 'route_id')
    def _onchange_product_availability(self):
        self._check_product_availability()

    @api.onchange('warehouse_location_id', 'route_id')
    def _onchange_int_location_route(self):
        if self.warehouse_location_id:
            self.route_id = False

    @api.onchange('product_type')
    def _onchange_product_type_location(self):
        if self.product_type in ('service', 'consu'):
            self.route_id = self.warehouse_location_id = False

    def _check_product_availability(self):
        for line in self:
            if line.product_type == 'product':
                if not line.route_id and not line.warehouse_location_id:
                    qty_to_check = line.product_id._get_qty_available_sale_location(
                        line.warehouse_id.lot_stock_id)
                    line.is_available = (qty_to_check >= line.product_uom_qty > 0)
                    continue
                if line.warehouse_location_id:
                    warehouse_location_stock = line.product_id._get_qty_available_sale_location(
                        line.warehouse_location_id) if line.warehouse_location_id.warehouse_id != line.warehouse_id else 0
                    qty_to_check = warehouse_location_stock
                    line.is_available = (qty_to_check >= line.product_uom_qty > 0)
                    continue
                if line.route_id.rule_ids and not line.warehouse_location_id:
                    route_location_stock = line.product_id._get_qty_available_sale_location(
                        line.route_id.rule_ids[0].location_src_id)
                    qty_to_check = route_location_stock
                    line.is_available = (qty_to_check >= line.product_uom_qty > 0)
            elif line.product_type in ('service', 'consu'):
                line.is_available = True

    def _create_internal_stock_moves(self, picking, internal_warehouse):
        """
        stock move creation for internal transfer
        :param picking, internal_warehouse:internal_warehouse_id
        :return stock moves:
        """
        values = []
        for line in self:
            if line.warehouse_location_id and line.internal_warehouse_id == internal_warehouse:
                for val in line._prepare_internal_stock_moves(picking, internal_warehouse):
                    values.append(val)
                line.internal_move_dest_ids.sale_line_id = False

        return self.env['stock.move'].sudo().create(values)

    def _prepare_internal_stock_moves(self, picking, internal_warehouse):
        """ Prepare the internal stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.internal_warehouse_id != internal_warehouse:
            return res
        if self.product_id.type not in ['product', 'consu'] and (not self.warehouse_location_id or not self.route_id):
            return res

        qty = 0.0
        price_unit = self._get_stock_move_price_unit()

        move_dests = self.internal_move_dest_ids
        if not move_dests:
            move_dests = self.move_ids.move_dest_ids.filtered(
                lambda m: m.state != 'cancel' and not m.location_dest_id.usage == 'internal')

        if not move_dests:
            qty_to_attach = 0
            qty_to_push = self.product_uom_qty - qty
        else:
            move_dests_initial_demand = self.product_id.uom_id._compute_quantity(
                sum(move_dests.filtered(
                    lambda m: m.state != 'cancel' and not m.location_dest_id.usage == 'internal').mapped(
                    'product_qty')),
                self.product_uom, rounding_method='HALF-UP')
            qty_to_attach = move_dests_initial_demand - qty
            qty_to_push = self.product_uom_qty - move_dests_initial_demand

        if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_attach,
                                                                                   self.product_id.uom_id)
            res.append(self._prepare_internal_stock_move_vals(picking, price_unit, product_uom))
        if float_compare(qty_to_push, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_push, self.product_id.uom_id)
            extra_move_vals = self._prepare_internal_stock_move_vals(picking, price_unit, product_uom)
            extra_move_vals['move_dest_ids'] = False  # don't attach
            res.append(extra_move_vals)
        return res

    def _prepare_internal_stock_move_vals(self, picking, price_unit, product_uom):
        self.ensure_one()
        location = False
        internal_qty = 0
        location_qty = self.product_id._get_qty_available_sale_location(self.warehouse_id.lot_stock_id)
        product = self.product_id.with_context(lang=self.env.user.lang)

        description_picking = product._get_description(self.order_id.warehouse_id.out_type_id)
        if self.warehouse_location_id:
            location = self.warehouse_location_id
            internal_qty = self.product_uom_qty
        date_planned = fields.Datetime.now()
        return {
            # truncate to 2000 to avoid triggering index limit error
            'name': (self.name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned + relativedelta(days=1),
            'location_id': location.id or False,
            'location_dest_id': self.order_id.transit_location.id if self.order_id.transit_location.id else self.warehouse_id.out_type_id.default_location_src_id.id,
            'picking_id': picking.id,
            'partner_id': self.order_id.partner_id.id,
            'move_dest_ids': [(4, x) for x in self.internal_move_dest_ids.ids],
            'state': 'draft',
            'sale_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.internal_picking_type_id.id,
            'group_id': self.order_id.procurement_group_id.id,
            'origin': self.order_id.name,
            'description_picking': description_picking,
            'propagate_cancel': self.propagate_cancel,
            'route_ids': [],
            'warehouse_id': self.order_id.warehouse_id.id,
            'product_uom_qty': internal_qty,
            'product_uom': product_uom.id,
        }

    def _get_stock_move_price_unit(self):
        self.ensure_one()
        line = self[0]
        order = line.order_id
        price_unit = line.price_unit
        if line.tax_id:
            price_unit = line.tax_id.with_context(round=False).compute_all(
                price_unit, currency=line.order_id.company_id.currency_id, quantity=1.0, product=line.product_id,
                partner=line.order_id.partner_id
            )['total_void']
        if line.product_uom.id != line.product_id.uom_id.id:
            price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, self.company_id,
                self.order_id.date or fields.Date.today(),
                round=False)
        return price_unit
