{
    'name': 'Financial Reports - Interactive Viewer',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Interactive financial reports with hierarchy expand/collapse like Enterprise',
    'description': """
        Interactive Financial Reports for Odoo 18 Community.
        
        Reports:
        - Trial Balance
        - Profit and Loss
        - Balance Sheet
        - General Ledger
        - Cash Flow Statement (Indirect Method)
        - Aging Report (AR and AP)
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'ac_coa_hierarchy',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ac_financial_reports/static/src/css/reports.css',
            'ac_financial_reports/static/src/js/report_action.js',
            'ac_financial_reports/static/src/xml/report_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
