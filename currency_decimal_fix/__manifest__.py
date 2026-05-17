# -*- coding: utf-8 -*-
{
    'name': 'Currency Decimal Precision Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Enforce fixed decimal precision: 3 digits for all currencies, 2 digits for IDR',
    'description': """
Currency Decimal Precision Fix
==============================
This module enforces mandatory decimal precision for all currencies:

- **All currencies**: 3 decimal digits (e.g., USD, EUR, GBP, SGD, etc.)
- **IDR (Indonesian Rupiah)**: 2 decimal digits

Rules are enforced at the ORM level and cannot be overridden via UI or standard Odoo settings.

Features:
---------
* Overrides default Odoo currency rounding values
* Hooks into currency write/create to enforce rules
* Patches decimal.precision records used across all modules
* Applies to: Accounting, Sales, Purchase, Stock, Invoicing, etc.
* Post-install hook to update all existing currencies
    """,
    'author': 'Custom Development',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/decimal_precision_data.xml',
        'data/currency_rounding_data.xml',
        'data/cron_data.xml',
        'views/res_currency_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': None,
}
