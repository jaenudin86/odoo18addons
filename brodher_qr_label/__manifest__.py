{
    'name': 'QR Code Serial Label',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Generate QR Code Label for Received Products',
    'depends': ['stock', 'product'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/qr_label_menu.xml',
        # 'report/qr_label_template.xml',
        'report/qr_label_report.xml',
    ],
    'installable': True,
    'application': False,
}