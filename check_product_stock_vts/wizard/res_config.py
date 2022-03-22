from odoo import fields,models,api

class res_config(models.TransientModel): 
    _inherit='res.config.settings'
        
    check_product_stock = fields.Selection([('warehouse_wise','Warehouse Wise'),('location_wise','Location Wise')],default='warehouse_wise',string='Check Product Stock')
    
    @api.model
    def get_values(self):
        res = super(res_config, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(                    
                    check_product_stock = params.get_param('check_product_stock_vts.check_product_stock',default='warehouse_wise')
                   )
        return res
    

    
    def set_values(self):
        super(res_config,self).set_values()
        ir_parameter = self.env['ir.config_parameter'].sudo()        
        ir_parameter.set_param('check_product_stock_vts.check_product_stock', self.check_product_stock)
        