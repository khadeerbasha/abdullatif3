# -*- coding: utf-8 -*-

# Python imports

# Odoo Imports
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError


class ShowroomRequestLine(models.Model):
    _name = 'showroom.request.line'
    _description = 'Lines of Showroom Request'
    _rec_name = 'product_id'
    _order = 'sequence'

    request_id = fields.Many2one(
        comodel_name='showroom.request',
        string='Request',
        required=True,
        index=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='sequence',
        default=10
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        index=True,
        domain="[('type', '!=', 'service')]"
    )
    product_uom_category_id = fields.Many2one(
        comodel_name='uom.category',
        related='product_id.uom_id.category_id'
    )
    quantity = fields.Float(
        string='Quantity',
        default=1
    )
    uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UoM',
        required=True,
        index=True,
        domain="[('category_id', '=', product_uom_category_id)]"
    )

    # Constrains methods
    @api.constrains('quantity')
    def _check_quantity(self):
        """
        Control on the Product quantity to verify if it's a valid value.
        :raise ValidationError
        :return Boolean
        """
        if any(line.quantity < 0 for line in self):
            raise ValidationError(
                _('The product quantity must be a valid positive value.')
            )
        return True

    # Onchange methods
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_id = self.product_id.uom_id

    # Business methods
    def _prepare_stock_move_values(self):
        """
        Prepare and return values used to create Stock Movement (stock.move).
        :return: dict
        """
        self.ensure_one()

        # Initialize variables
        request = self.request_id

        return {
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'location_id': request.location_src_id.id,
            'location_dest_id': request.location_dest_id.id,
            'product_uom': self.uom_id.id,
            'product_uom_qty': self.quantity,
        }


class ShowroomRequest(models.Model):
    _name = 'showroom.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Showroom Request'

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        readonly=True,
        copy=False,
        default='New Request'
    )
    line_ids = fields.One2many(
        comodel_name='showroom.request.line',
        inverse_name='request_id',
        string='Products',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Operation Type',
        index=True,
        required=True,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('code', '=', 'internal')]"
    )
    picking_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='showroom_request_id',
        string='Stock Operations',
        readonly=True,
    )
    picking_count = fields.Integer(
        compute='_compute_picking_count'
    )
    location_src_id = fields.Many2one(
        comodel_name='stock.location',
        string='Source Location',
        required=True,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('usage', '=', 'internal')]"
    )
    location_dest_id = fields.Many2one(
        comodel_name='stock.location',
        string='Destination Location',
        required=True,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('usage', '=', 'internal')]"
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ],
        default='draft',
        index=True,
        required=True,
        tracking=True,
        readonly=True,
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        required=True,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    user_submit_id = fields.Many2one(
        comodel_name='res.users',
        string='Submitted By',
        readonly=True,
    )
    user_approve_id = fields.Many2one(
        comodel_name='res.users',
        string='Approved By',
        readonly=True,
    )

    # Onchange methods
    @api.onchange('picking_type_id')
    def _onchange_picking_type(self):
        if self.picking_type_id:
            self.location_src_id = self.picking_type_id.default_location_src_id
            self.location_dest_id = self.picking_type_id.default_location_dest_id

    # Compute methods
    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for request in self:
            request.picking_count = len(request.picking_ids)

    # Button methods
    def button_submit(self):
        """
        Action method called from the view to change the status of the request to 'to_approve'
        """
        # Initialize Variables
        current_user = self.env.user
        IrSequence = self.env['ir.sequence']

        for request in self:
            if request.state != 'draft':
                raise ValidationError(
                    _('Only draft requests can be submitted.')
                )

            if not request.line_ids.filtered(lambda l: l.quantity > 0):
                raise ValidationError(
                    _('No product to transfer. Please insert some products/quantities on the the below product list.')
                )

            request.write({
                'state': 'to_approve',
                'user_submit_id': current_user.id,
                'name': IrSequence.next_by_code('showroom.request'),
            })

    def button_approve(self):
        """
        Action method called from the view to change the status of the request to 'done'
        """
        if any(request.state != 'to_approve' for request in self):
            raise ValidationError(
                _('Only draft requests can be approved.')
            )

        # Create Stock operation
        self._create_stock_picking()

        # Initialize Variables
        current_user = self.env.user

        # Update 'status' & 'Submitted by'
        self.write({
            'state': 'done',
            'user_approve_id': current_user.id
        })

    def button_reject(self):
        """
        Action method called from the view to change the status of the request to 'rejected'
        """
        if any(request.state != 'to_approve' for request in self):
            raise ValidationError(
                _('Only draft requests can be rejected.')
            )
        self.write({
            'state': 'rejected'
        })

    # Action methods
    def action_view_picking(self):
        self.ensure_one()
        if not self.picking_ids:
            return
        return {
            'name': _('Stock Transfers'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': {
                'default_showroom_request_id': self.id
            }
        }

    # Business methods
    def _prepare_stock_picking_values(self):
        """
        Prepare and return the dictionary of values will be user to create a stock operation
        :return: dict
        """
        self.ensure_one()
        moves = [Command.create(line._prepare_stock_move_values()) for line in self.line_ids]
        return {
            'picking_type_id': self.picking_type_id.id,
            'location_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'move_ids_without_package': moves,
            'showroom_request_id': self.id,
        }

    def _create_stock_picking(self):
        """
        Create Stock Operation (stock.picking) for every Request.
        :return: list(stock.picking)
        """
        # Initialize variables
        StockPicking = self.env['stock.picking']
        values = [request._prepare_stock_picking_values() for request in self]

        return StockPicking.create(values)

    # CRUD Methods
    def unlink(self):
        if any(request.state != 'draft' for request in self):
            raise ValidationError(
                _('Only draft requests can be removed')
            )
        return super(ShowroomRequest, self).unlink()
