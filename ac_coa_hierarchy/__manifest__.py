{
    'name': 'CoA Hierarchy - Parent Child',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Menambahkan struktur parent-child pada Chart of Accounts seperti Accurate',
    'description': """
        Modul ini menambahkan fitur hierarki parent-child pada Chart of Accounts (CoA) di Odoo Community.
        
        Fitur:
        - Field parent_id pada account.account
        - Tree view hierarkis dengan expand/collapse
        - Computed field: level, complete_name, child_ids
        - Validasi circular reference
        - Kompatibel dengan Account Groups bawaan Odoo
    """,
    'author': 'Custom',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_account_views.xml',
        'views/menu.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
    'auto_install': False,
}
