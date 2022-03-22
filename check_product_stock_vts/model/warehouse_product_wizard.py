from odoo import api, fields, models, _


class WarehouseProductWizard(models.TransientModel):
    _name = 'warehouse.product.wizard'

    warehouse_product_ids = fields.One2many('warehouse.product.stock', 'warehouse_product_id',
                                            string='Warehouse Products')

    @api.model
    def default_get(self, default_fields):
        res = super(WarehouseProductWizard, self).default_get(default_fields)
        if self._context.get('active_model') == 'sale.order.line':
            stock_quant = self.env['stock.quant']
            product = self.env['product.product'].browse(self._context.get('product_id'))
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)])
            quant_obj = self.env['stock.quant'].search([('product_id', '=', product.id)])
            product_warehouse_stock_data = []
            check_product_stock = self.env['ir.config_parameter'].sudo().get_param(
                'check_product_stock_vts.check_product_stock')
            if check_product_stock == 'warehouse_wise':
                for record in warehouse:
                    available_qty = product.with_context(location=record.lot_stock_id.id).qty_available
                    available_qty_for_sale = product._get_qty_available_sale_location(record.lot_stock_id)
                    available_qty_on_hand = stock_quant._get_available_quantity(product_id=product,
                                                                                         location_id=record.lot_stock_id,
                                                                                         lot_id=None,
                                                                                         package_id=None,
                                                                                         owner_id=None,
                                                                                         strict=False)
                    if (available_qty and available_qty_for_sale and available_qty_on_hand) > 0:
                        product_warehouse_stock_data.append((0, 0, {
                            'product_id': product.id,
                            'warehouse_id': record.id,
                            'location_id': record.lot_stock_id.id,
                            'available_qty_on_hand': available_qty_on_hand,
                            'available_qty_for_sale': available_qty_for_sale,
                            'qty': available_qty,
                        }))
            else:
                for quant in quant_obj:
                    available_qty = quant.quantity
                    if available_qty > 0.0 and quant.location_id.usage == 'internal':
                        available_qty_for_sale = product._get_qty_available_sale_location(quant.location_id)
                        available_qty_on_hand = stock_quant._get_available_quantity(product_id=product,
                                                                                    location_id=quant.location_id,
                                                                                    lot_id=None,
                                                                                    package_id=None,
                                                                                    owner_id=None,
                                                                                    strict=False)
                        if (available_qty_for_sale and available_qty_on_hand) > 0:
                            product_warehouse_stock_data.append((0, 0, {
                                'product_id': product.id,
                                # 'warehouse_id':record.id,
                                'location_id': quant.location_id.id,
                                'qty': available_qty,
                                'available_qty_on_hand': available_qty_on_hand,
                                'available_qty_for_sale': available_qty_for_sale,
                            }))

            res.update({'warehouse_product_ids': product_warehouse_stock_data})
        return res
