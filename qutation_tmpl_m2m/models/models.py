# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class qutation_tmpl_m2m(models.Model):
#     _name = 'qutation_tmpl_m2m.qutation_tmpl_m2m'
#     _description = 'qutation_tmpl_m2m.qutation_tmpl_m2m'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
