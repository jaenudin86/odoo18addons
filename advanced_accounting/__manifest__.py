# -*- coding: utf-8 -*-
{
    'name': 'Advanced Accounting',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Advanced Accounting Features - Enterprise-like',
    'description': """
        Advanced Accounting Module for Odoo 18
        =====================================
        
        Features:
        ---------
        * Budget Management
        * Asset Management
        * Analytic Accounting
        * Multi-Currency Support
        * Advanced Reports
        * Bank Reconciliation
        * Payment Follow-up
        * Invoice Approval Workflow
        * Fiscal Year Management
        * Cost Center Management
        * Tax Reports
        * Financial Dashboard
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        # 'account_accountant',
    ],
    'data': [
        'security/accounting_security.xml',
        'security/ir.model.access.csv',
        'data/account_data.xml',
        'views/account_budget_views.xml',
        'views/account_asset_views.xml',
        'views/account_analytic_views.xml',
        'views/account_payment_followup_views.xml',
        'views/account_cost_center_views.xml',
        'views/account_report_views.xml',
        'views/account_dashboard_views.xml',
        'views/menu_views.xml',
        'wizard/account_budget_wizard_views.xml',
        'wizard/account_report_wizard_views.xml',
        'reports/account_report_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
