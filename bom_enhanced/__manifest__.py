{
    'name': 'BOM Enhanced Reports',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Enhanced BOM with Serial Number and Professional Reports',
    'description': """
        Enhanced BOM Module for Odoo 18
        =================================
        Features:
        * Automatic Serial Number for each BOM
        * Sales Order reference field (optional)
        * Report with prices (costing analysis)
        * Report without prices (technical specification)
        * Professional layout with company logo and address
        * Modern and clean design
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['mrp', 'sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/mrp_bom_views.xml',
        'reports/bom_reports.xml',
        'reports/bom_report_with_price.xml',
        'reports/bom_report_no_price.xml',
        'reports/bom.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'bom_enhanced/static/src/css/report_style.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
