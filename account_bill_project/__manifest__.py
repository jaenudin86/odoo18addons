# -*- coding: utf-8 -*-
{
    'name': 'Account Bill Project',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Vendor Bills dengan Analytic Header, COA Lines, dan Approval Workflow',
    'description': """
Account Bill Project
====================
Fitur:
- Account Analytic di header (otomatis berlaku untuk semua baris)
- Baris tagihan langsung input COA (bukan produk)
- Approval workflow (Finance Manager dan Direktur Keuangan)
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
        # 'views/res_config_settings_views.xml',
        'views/menus.xml',
        'wizard/bill_approval_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
