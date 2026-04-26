# -*- coding: utf-8 -*-
{
    'name': 'Product Serial API',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Products',
    'summary': 'REST API to get product variant info by serial number',
    'description': """
        Provides a REST API endpoint to retrieve product variant information
        based on serial number (lot). Designed for integration with external
        systems such as Laravel web apps.

        Endpoint:
            GET /api/product/serial/<serial_number>

        Authentication:
            Header: X-API-Key: <your_api_key>
    """,
    'author': 'Custom',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
