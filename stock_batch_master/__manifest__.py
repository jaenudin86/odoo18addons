{
    'name': 'Stock Batch Master',
    'version': '18.0.1.0.0',
    'summary': 'Add Batch Number master and link to Serial/Lot Numbers',
    'description': """
        - Adds master data for Batch Numbers
        - Links Batch Number (Many2one) to stock.lot (Serial/Lot)
        - Batch Number + Expiration Date melekat pada Serial Number
    """,
    'category': 'Inventory',
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_batch_master_views.xml',
        'views/stock_lot_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
