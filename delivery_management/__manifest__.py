# -*- coding: utf-8 -*-
{
    'name': 'Delivery Management',
    'version': '1.0.0',
    'category': 'Hidden',
    'author': 'Abderrahmane Guessoum - Alpha Brains Technologies',
    'website': 'www.fiverr.com/aabcrow',
    'depends': [
        'sale_management',
        'stock',
        'helpdesk',
        'showroom_request',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_management_views.xml',
        'views/stock_views.xml',
        'wizard/reschedule_delivery_order_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    
}
