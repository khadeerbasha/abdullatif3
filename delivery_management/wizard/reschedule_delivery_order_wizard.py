from odoo import models, fields, api, tools, _

from odoo.exceptions import ValidationError
from datetime import timedelta


class RescheduleDeliveryWizard(models.TransientModel):
    _name = 'reschedule.delivery.wizard'
    _description = 'Reschedule Delivery Wizard'

    date = fields.Datetime(
        'Date to reschedule',
        required=True
    )
    reason = fields.Text(
        string="Reason",
    )

    def confirm(self):
        if self.env.context.get('active_id'):
            active_id = self.env.context.get('active_id')
            picking = self.env['stock.picking']
            picking_id = picking.browse(active_id)
            picking_id.write({
                'scheduled_date': self.date,
                'tracking_state': 'reschedule'
            }
            )
            msg = _("New scheduled date :  %s <br>"
                    "Reason : %s") % (self.date, self.reason)
            picking_id.message_post(body=msg)
            return self.env.ref('delivery_management.act_window_delivery_management_dashboard').sudo().read()[0]
