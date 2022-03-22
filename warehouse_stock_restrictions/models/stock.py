# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, AccessError


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.constrains('state', 'location_id', 'location_dest_id')
    def check_user_location_rights(self):
        # self.ensure_one()
        # if self.state == 'draft':
        #   return True
        user_locations = self.env.user.stock_location_ids
        print(user_locations)
        print("Checking access %s" % self.env.user.default_picking_type_ids)
        if self.env.user.restrict_locations and self.env.user.stock_location_ids and self.state == "done":
            # message = _(
            # 'Invalid Location. You cannot process this move since you do '
            # 'not control the location "%s". '
            # 'Please contact your Adminstrator.')
            # if self.location_id not in user_locations:
            # raise Warning(message % self.location_id.name)
            # elif self.location_dest_id not in user_locations:
            # raise Warning(message % self.location_dest_id.name)
            if self.location_dest_id not in user_locations:
                raise ValidationError(
                    'You cannot process this move since you do not have control on destination location')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        user_locations = self.env.user.stock_location_ids
        if self.env.user.restrict_locations:
            if user_locations:
                if self.location_id not in user_locations:
                    raise ValidationError('You cannot process this move since you do not have control on destination')
        return res
