# -*- coding: utf-8 -*-
{
    'name': 'Work Center Custom Code',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Custom Work Center coding format with Division and Department',
    'description': """
        Custom Work Center Module
        =========================
        * Adds Division ID and Division Name fields
        * Auto-generates work center code with format: EQT.[DEPT].[CODE].00000
        * Supports Office (OFF) and Manufacturing (MFR) departments
        * Compatible with Odoo 18
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_workcenter_views.xml',
    ],
    'demo': [
        'data/workcenter_demo_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
