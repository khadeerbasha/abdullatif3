# -*- coding: utf-8 -*-

{
    'name': "Journal Restrictions",
    'summary': """Restrict users to certain journals""",
    'description': """Restrict users to certain journals.""",
    'author': "ME",
    'website': "http://www.mycompany.com",
    'license': 'AGPL-3',
    'category': 'account',
    'version': '15',
    'depends': ['account'],
    'data': [
        'views/users.xml',
        'security/security.xml',
    ],
    "images": [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
