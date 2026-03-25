# -*- coding: utf-8 -*-
{
    'name': 'Account Bill Project',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Vendor Bills with Analytic Header, COA Lines, and Approval Workflow',
    'description': """
Account Bill Project
====================
Fitur:
- Account Analytic di header (otomatis ikut semua baris)
- Item baris menggunakan COA (bukan produk)
- Approval workflow (Finance Manager & Direktur Keuangan)
- Attachment opsional (tidak wajib)
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'analytic',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/account_bill_project_security.xml',
        'views/account_move_views.xml',
        'views/account_bill_approval_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/bill_approval_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_bill_project/static/src/js/analytic_sync.js',
            'account_bill_project/static/src/css/account_bill_project.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
