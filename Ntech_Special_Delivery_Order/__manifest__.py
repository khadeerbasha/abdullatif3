# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Special Delivery Account',
    'version': '13.0',
    'author' : 'khadeer',
    'category': 'Inventory',
    'description': """Special Delivery Account""",
    'depends': ['stock','stock_account','Ntech_Stock_Analytic'],
    'website':'http://www.nutechits.com/',
    'data': ['views/special_delivery_order_view.xml'],
    'installable': True,
    'auto install':False,
    'application':True,
}
