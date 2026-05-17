# -*- coding: utf-8 -*-
{
    'name': 'Stock Internal Transfer Approval',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Approval workflow for internal stock transfers',
    'description': """
        Adds an approval system to internal stock transfers.

        Features:
        - Checkbox on Operation Type (internal only) to enable approval workflow
        - 'Internal Transfer Creator' checkbox on user: can create internal transfers
        - 'Internal Transfer Approver' checkbox on user: can approve/refuse transfers
        - Approval workflow states: Draft → Waiting Approval → Approved → Done
        - Approver cannot approve their own transfer
        - Transfer cannot be validated without approval when required
    """,
    'author': 'Custom Development',
    'depends': ['stock'],
    'data': [
        'security/stock_internal_approval_security.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
