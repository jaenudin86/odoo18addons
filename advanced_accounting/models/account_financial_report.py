# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountFinancialReport(models.Model):
    _name = 'account.financial.report'
    _description = 'Financial Report'
    _order = 'sequence, name'

    name = fields.Char('Report Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    
    parent_id = fields.Many2one('account.financial.report', 'Parent Report',
                               domain="[('id', '!=', id)]")
    child_ids = fields.One2many('account.financial.report', 'parent_id', 
                               'Child Reports')
    
    type = fields.Selection([
        ('sum', 'Sum'),
        ('accounts', 'Accounts'),
        ('account_type', 'Account Type'),
        ('account_report', 'Report Value'),
    ], default='sum', required=True, string='Type')
    
    account_ids = fields.Many2many('account.account', 
                                   'account_financial_report_account_rel',
                                   'report_id', 'account_id', 'Accounts')
    account_type_ids = fields.Many2many('account.account.type',
                                        'account_financial_report_type_rel',
                                        'report_id', 'account_type_id',
                                        'Account Types')
    account_report_id = fields.Many2one('account.financial.report', 'Report')
    
    sign = fields.Selection([
        ('-1', 'Reverse Sign (Payables, Expenses)'),
        ('1', 'Normal Sign (Assets, Receivables)'),
    ], default='1', required=True, help='For accounts that show a debit amount, the sign is 1. For accounts that show a credit amount, the sign is -1.')
    
    display_detail = fields.Selection([
        ('no_detail', 'No Detail'),
        ('detail_flat', 'Detail with Line Breaks'),
        ('detail_with_hierarchy', 'Detail with Hierarchy'),
    ], default='detail_flat', string='Display Detail')
    
    style_overwrite = fields.Selection([
        ('0', 'Automatic Formatting'),
        ('1', 'Main Title (bold, underline)'),
        ('2', 'Title 2 (bold)'),
        ('3', 'Title 3 (bold, smaller)'),
        ('4', 'Normal Text'),
        ('5', 'Italic Text'),
        ('6', 'Smaller Text'),
    ], default='0', string='Financial Report Style')
    
    company_id = fields.Many2one('res.company', 'Company')
    
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive reports.'))


class AccountFinancialReportLine(models.Model):
    _name = 'account.financial.report.line'
    _description = 'Financial Report Line'
    
    report_id = fields.Many2one('account.financial.report', 'Report', required=True)
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    company_id = fields.Many2one('res.company', 'Company')
    
    balance = fields.Monetary('Balance', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
