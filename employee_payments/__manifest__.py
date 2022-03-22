{
    'name': 'Hr Employee Payments',
    'version': '15.0',
    'category': 'Human Resources',
	'author' : 'me',
    'description': """Hr Employee Payments""",
    'depends': ['hr','hr_holidays','account','hr_contract','hr_payroll'],
    'website':'http://www.me.com/',
    'data': [
            'views/hr_employee_voucher_view.xml',
            'views/employee_report_voucher_templates.xml',
            'views/employee_voucher_report.xml',
            'views/cron_view.xml',
            'security/ir.model.access.csv',
            ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}