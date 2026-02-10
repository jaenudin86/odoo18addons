# -*- coding: utf-8 -*-
{
    'name': 'POS & Warehouse User Access Control',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Manage user access to specific POS and Warehouses',
    'description': """
        POS & Warehouse User Access Control
        ====================================
        
        Features:
        ---------
        * Assign specific POS to users (many2many)
        * Assign specific Warehouses to users (many2many)
        * Users can only access assigned POS
        * Users can only view stock from assigned warehouses
        * Admin can see which users have access to specific POS/Warehouse
        * Automatic filtering based on user access rights
        
        Usage:
        ------
        1. Go to Settings > Users & Companies > Users
        2. Select a user and assign POS and Warehouses in the new tabs
        3. User will only see assigned POS and warehouse stock
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'point_of_sale',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/res_users_views.xml',
        'views/pos_config_views.xml',
        'views/stock_warehouse_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
