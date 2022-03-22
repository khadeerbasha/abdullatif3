# -*- coding: utf-8 -*-
# Odoo Imports
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    internal_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Internal picking type',
        domain=[("code", "=", "internal")]
    )
    all_available_ok = fields.Boolean(
        compute='_compute_all_available_ok'
    )
    transit_location = fields.Many2one(
        comodel_name='stock.location',
        string='Transit Location',
        domain="[('usage', '=', 'transit'),('warehouse_id_stored','=',warehouse_id)]",
        default=lambda self: self.warehouse_id.wh_transit_loc_id,
    )
    delivery_count_internal = fields.Integer(
        string="Delivery Count INT",
        compute='_compute_picking_ids'
    )

    # Onchange Methods
    @api.onchange('warehouse_id')
    def _get_internal_picking_type_id(self):
        picking_type = self.env['stock.picking.type'].search(
            [('code', '=', 'internal'), ('warehouse_id', '=', self.warehouse_id.id),
             ('warehouse_id.company_id', '=', self.env.user.company_id.id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'internal'), ('warehouse_id', '=', self.warehouse_id.id)])
        transit_location = self.warehouse_id.wh_transit_loc_id
        self.internal_picking_type_id = picking_type[:1]
        if transit_location:
            self.transit_location = transit_location
        else:
            self.transit_location = False
        self.action_check_product_availability()

    # Compute Methods
    @api.depends('order_line.is_available')
    def _compute_all_available_ok(self):
        for order in self:
            order.all_available_ok = all(line.is_available for line in order.order_line)

    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for order in self:
            picking_out = self.mapped('picking_ids').filtered(lambda l: l.picking_type_code == 'outgoing')
            picking_int = self.mapped('picking_ids').filtered(lambda l: l.picking_type_code == 'internal')
            order.delivery_count = len(picking_out)
            order.delivery_count_internal = len(picking_int)

    def action_check_product_availability(self):
        for line in self.order_line:
            line._check_product_availability()

    def _check_products_availability(self):
        if any(line.is_available is False and line.product_id.type == "product" for line in self.order_line):
            raise ValidationError(
                _("There is at least an unavailable product, please check your sale lines then proceed !")
            )

    def action_confirm(self):
        self.action_check_product_availability()
        self._check_products_availability()
        return super(SaleOrder, self).action_confirm()

    def _action_confirm(self):
        self.order_line._action_launch_stock_rule()
        self._create_transfer_pickings()
        picking_out = self.mapped('picking_ids').filtered(lambda l: l.picking_type_code == 'outgoing')
        picking_int = self.mapped('picking_ids').filtered(lambda l: l.picking_type_code == 'internal')
        if len(picking_out) == 1 and len(picking_int) > 0:
            picking_out.do_unreserve()
        return super(SaleOrder, self)._action_confirm()

    def action_view_delivery_internal(self):
        picking_int = self.mapped('picking_ids').filtered(lambda l: l.picking_type_code == 'internal')
        return self._get_action_view_picking(picking_int)

    def action_view_delivery(self):
        picking_out = self.mapped('picking_ids').filtered(lambda l: l.picking_type_code == 'outgoing')
        return self._get_action_view_picking(picking_out)

    def _prepare_transfer_picking(self, internal_warehouse):
        if not self.procurement_group_id:
            self.procurement_group_id = self.procurement_group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id,
                'sale_id': self.id
            })
        return {
            'picking_type_id': internal_warehouse.int_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.commitment_date,
            'origin': self.name,
            'location_dest_id': self.transit_location.id if self.transit_location.id else self.warehouse_id.out_type_id.default_location_src_id.id,
            'location_id': internal_warehouse.int_type_id.default_location_src_id.id,
            'company_id': self.company_id.id,
            'sale_id': self.id,
            'group_id': self.procurement_group_id.id,
        }

    def _create_transfer_picking(self, internal_warehouse):
        StockPicking = self.env['stock.picking']
        for order in self:
            if any(product.type in ['product', 'consu'] for product in order.order_line.product_id) and any(
                    line.route_id or line.warehouse_location_id for line in order.order_line):
                order = order.with_company(order.company_id)
                res = order.sudo()._prepare_transfer_picking(internal_warehouse)
                picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                moves = order.order_line.sudo()._create_internal_stock_moves(picking, internal_warehouse)
                moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date):
                    seq += 5
                    move.sequence = seq
                moves._action_assign()
                picking.message_post_with_view('mail.message_origin_link',
                                               values={'self': picking, 'origin': order},
                                               subtype_id=self.env.ref('mail.mt_note').id)
        return True

    def _create_transfer_pickings(self):
        for order in self:
            internal_warehouse_ids = order.order_line.mapped('internal_warehouse_id')
            for wh in internal_warehouse_ids:
                order.sudo()._create_transfer_picking(wh)

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if self.state not in ('done', 'sale'):
            self.action_check_product_availability()
        return res
