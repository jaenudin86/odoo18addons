# -*- coding: utf-8 -*-
{
    'name': 'Account Bill Project',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Vendor Bills — Jurnal Bank/Kas, COA Lines, Analytic Header, Approval, PDF Report',
    'description': """
Account Bill Project
====================
- Jurnal otomatis filter Bank & Kas saja
- Baris tagihan langsung input COA (tanpa produk)
- Account Analytic di header (sync ke semua baris)
- Approval workflow (Finance Manager + Direktur)
- PDF Report tagihan vendor
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
        # 'report/report_vendor_bill.xml',
        # 'report/report_action.xml',
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
