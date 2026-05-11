# -*- coding: utf-8 -*-
{
    'name': 'WooCommerce Connector Pro',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Professional WooCommerce Odoo Integration',
    'description': """
        Market-ready WooCommerce Connector for Odoo 18.
        - Multi-instance support
        - Product, Category, and Attribute Sync
        - Inventory Sync
        - Order and Customer Import
        - Detailed Sync Logs
    """,
    'author': 'Custom Development',
    'website': 'https://www.yourwebsite.com',
    'license': 'LGPL-3',
    'depends': ['base', 'sale_management', 'stock', 'product'],
    'external_dependencies': {
        'python': ['woocommerce'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'wizard/woo_operation_wizard_views.xml',
        'views/woo_backend_views.xml',
        'views/woo_sync_log_views.xml',
        'views/woo_mapping_views.xml',
        'views/woo_menus.xml',
    ],
    'installable': True,
    'application': True,
}
