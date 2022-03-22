# -*- coding: utf-8 -*-
# from odoo import http


# class QutationTmplM2m(http.Controller):
#     @http.route('/qutation_tmpl_m2m/qutation_tmpl_m2m', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/qutation_tmpl_m2m/qutation_tmpl_m2m/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('qutation_tmpl_m2m.listing', {
#             'root': '/qutation_tmpl_m2m/qutation_tmpl_m2m',
#             'objects': http.request.env['qutation_tmpl_m2m.qutation_tmpl_m2m'].search([]),
#         })

#     @http.route('/qutation_tmpl_m2m/qutation_tmpl_m2m/objects/<model("qutation_tmpl_m2m.qutation_tmpl_m2m"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('qutation_tmpl_m2m.object', {
#             'object': obj
#         })
