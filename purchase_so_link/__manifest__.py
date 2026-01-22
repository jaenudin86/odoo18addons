# -*- coding: utf-8 -*-
{
    'name': 'Purchase Order SO Link',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Link Purchase Orders to Sales Orders with Amount Validation',
    'description': """
        Purchase Order SO Link
        ======================
        * Link Purchase Orders to Sales Orders
        * Validate that total purchase amount does not exceed SO amount
        * Generate reports showing SO to PO relationships
        * Accounting reports for tracking
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['purchase', 'sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
        'reports/purchase_so_report_template.xml',
        # 'reports/purchase_so_report.xml',
        # 'reports/account_purchase_so_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
