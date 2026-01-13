# -*- coding: utf-8 -*-
{
    'name': 'Brodher Product Serial Number',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Custom Serial Number Generator with QR Code',
    'description': """
        Brodher Product Serial Number Management
        =========================================
        
        Features:
        ---------
        * Generate custom serial numbers (Format: PF + Year + Type + Sequence)
        * Auto-generate QR codes for all serial numbers
        * Scan serial numbers via QR code or manual selection
        * Track serial number movements (in/out/internal)
        * Support multi-step warehouse operations
        * Integration with Purchase and Sales orders
        * Custom reports with QR code labels
        * Product type classification (Man/Woman)
    """,
    'author': 'Brodher',
    'website': 'https://www.brodher.com',
    'license': 'LGPL-3',
    'depends': ['product', 'stock', 'purchase', 'sale'],
    'external_dependencies': {'python': ['qrcode', 'pillow']},
    'data': [
        'security/ir.model.access.csv',
        'wizard/message_wizard_views.xml',
        'wizard/product_sn_wizard_views.xml',
        # 'wizard/scan_sn_wizard_views.xml',
        'wizard/scan_sn_in_wizard_views.xml',      # BARU
        'wizard/scan_sn_out_wizard_views.xml',     # BARU
        'wizard/sn_validation_wizard_views.xml',
        'views/product_template_views.xml',
        'views/stock_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/sn_move_views.xml',
        'reports/sn_qr_label_report.xml',
        'reports/stock_picking_qrcode_report.xml',
        'wizard/product_qrcode_label_wizard_view.xml',
        'reports/paperformat.xml',
        'reports/product_qrcode_label_report.xml',
        'reports/product_qrcode_label_template.xml',
        # 'wizard/stock_picking_sn_wizard_views.xml',  # NEW
        'wizard/brodher_stock_picking_sn_wizard_views.xml',  # NEW
         'report/serial_number_qrcode_report.xml',  # ← TAMBAHKAN INI

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}