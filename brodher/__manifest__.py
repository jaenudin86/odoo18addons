# -*- coding: utf-8 -*-
{
    'name': "brodher",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    # 'depends': ['product','web'],
'depends': ['stock', 'website', 'product'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
    'views/product_ingredients.xml',
    'views/scan_barcode_template.xml',
     'views/scan_barcode_view.xml',
    'views/scan_barcode_menu.xml',
    # 'reports/stock_picking_qrcode_report.xml',
    # 'reports/stock_picking_qrcode_template.xml',
    'reports/stock_picking_qrcode_action.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

