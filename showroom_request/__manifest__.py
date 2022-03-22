# -*- coding: utf-8 -*-
{
    'name': 'Showroom Request',
    'version': '1.0.0',
    'category': 'Hidden',
    'author': 'Mohamed Lamine Lalmi',
    'website': 'www.fiverr.com/mohamedlaminela',
    'depends': [
        'stock',
        'sale_management',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/showroom_request_views.xml',
        'data/ir_sequence_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
