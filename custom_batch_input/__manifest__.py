{
    'name': 'Custom Batch & Expiry Input Wizard',
    'version': '18.0.2.0.0',
    'summary': 'Input batch number dan expired date saat penerimaan barang',
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['stock', 'purchase_stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/stock_batch_input_wizard_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
