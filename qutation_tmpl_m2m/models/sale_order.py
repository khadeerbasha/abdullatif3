
from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import is_html_empty



class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_template_id = fields.Many2many(
        comodel_name='sale.order.template', string='Quotation Template',
        readonly=True, check_company=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.model
    def default_get(self, fields_list):
        default_vals = super(SaleOrder, self).default_get(fields_list)
        if "sale_order_template_id" in fields_list and not default_vals.get("sale_order_template_id"):
            company_id = default_vals.get('company_id', False)
            company = self.env["res.company"].browse(company_id) if company_id else self.env.company
            #change id to ids to get all ads of m2m
            default_vals['sale_order_template_id'] = company.sale_order_template_id.ids
        return default_vals

    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):

        if not self.sale_order_template_id:
            self.require_signature = self._get_default_require_signature()
            self.require_payment = self._get_default_require_payment()
            return

        templates = self.sale_order_template_id.with_context(lang=self.partner_id.lang)


        order_lines = [(5, 0, 0)]
        # add templates in to forloop to get each tempalte options and lins and change with each one
        for template in templates:
            for line in template.sale_order_template_line_ids:
                data = self._compute_line_data_for_template_change(line)
                if line.product_id:
                    price = line.product_id.lst_price
                    discount = 0

                    if self.pricelist_id:
                        pricelist_price = self.pricelist_id.with_context(uom=line.product_uom_id.id).get_product_price(line.product_id, 1, False)

                        if self.pricelist_id.discount_policy == 'without_discount' and price:
                            discount = max(0, (price - pricelist_price) * 100 / price)
                        else:
                            price = pricelist_price

                    data.update({
                        'price_unit': price,
                        'discount': discount,
                        'product_uom_qty': line.product_uom_qty,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom_id.id,
                        'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
                    })

                order_lines.append((0, 0, data))

            self.order_line = order_lines
            self.order_line._compute_tax_id()

            # then, process the list of optional products from the template
            option_lines = [(5, 0, 0)]
            for option in template.sale_order_template_option_ids:
                data = self._compute_option_data_for_template_change(option)
                option_lines.append((0, 0, data))

            self.sale_order_option_ids = option_lines

            if template.number_of_days > 0:
                self.validity_date = fields.Date.context_today(self) + timedelta(template.number_of_days)

            self.require_signature = template.require_signature
            self.require_payment = template.require_payment

            if not is_html_empty(template.note):
                self.note = template.note
