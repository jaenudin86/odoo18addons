# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class AccountAsset(models.Model):
    _name = 'account.asset'
    _description = 'Asset Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Asset Name', required=True, tracking=True)
    code = fields.Char('Asset Code', tracking=True)
    
    asset_type = fields.Selection([
        ('purchase', 'Purchase'),
        ('sale', 'Sale')
    ], default='purchase', required=True, string='Asset Type', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('close', 'Closed')
    ], default='draft', string='Status', tracking=True)
    
    date = fields.Date('Asset Date', required=True, 
                       default=fields.Date.today, tracking=True)
    first_depreciation_date = fields.Date('First Depreciation Date', 
                                          tracking=True)
    
    original_value = fields.Monetary('Original Value', required=True, 
                                     currency_field='currency_id', tracking=True)
    salvage_value = fields.Monetary('Salvage Value', 
                                    currency_field='currency_id', tracking=True)
    book_value = fields.Monetary('Book Value', compute='_compute_book_value', 
                                 store=True, currency_field='currency_id')
    value_residual = fields.Monetary('Residual Value', compute='_compute_book_value',
                                     store=True, currency_field='currency_id')
    
    method = fields.Selection([
        ('linear', 'Linear'),
        ('degressive', 'Degressive'),
    ], default='linear', required=True, string='Computation Method')
    method_number = fields.Integer('Number of Depreciations', default=5)
    method_period = fields.Selection([
        ('1', 'Monthly'),
        ('3', 'Quarterly'),
        ('12', 'Yearly'),
    ], default='12', required=True, string='Period Length')
    method_progress_factor = fields.Float('Degressive Factor', default=0.3)
    
    prorata = fields.Boolean('Prorata Temporis', 
                            help='Indicates that the first depreciation entry will be prorated')
    
    account_asset_id = fields.Many2one('account.account', 'Asset Account', 
                                       required=True, domain=[('account_type', '=', 'asset_fixed')])
    account_depreciation_id = fields.Many2one('account.account', 
                                              'Depreciation Account', required=True)
    account_depreciation_expense_id = fields.Many2one('account.account', 
                                                      'Expense Account', required=True)
    
    journal_id = fields.Many2one('account.journal', 'Journal', required=True,
                                 domain=[('type', '=', 'general')])
    
    company_id = fields.Many2one('res.company', 'Company', 
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    
    partner_id = fields.Many2one('res.partner', 'Partner')
    invoice_id = fields.Many2one('account.move', 'Invoice', 
                                 domain=[('move_type', 'in', ['in_invoice', 'in_refund'])])
    
    depreciation_line_ids = fields.One2many('account.asset.depreciation.line', 
                                            'asset_id', 'Depreciation Lines')
    
    note = fields.Text('Notes')
    
    @api.depends('original_value', 'salvage_value', 'depreciation_line_ids.move_check',
                 'depreciation_line_ids.amount')
    def _compute_book_value(self):
        for asset in self:
            posted_lines = asset.depreciation_line_ids.filtered(lambda x: x.move_check)
            total_depreciation = sum(posted_lines.mapped('amount'))
            asset.book_value = asset.original_value - total_depreciation
            asset.value_residual = asset.book_value - asset.salvage_value
    
    def action_validate(self):
        self.write({'state': 'open'})
        return self.compute_depreciation_board()
    
    def action_close(self):
        self.write({'state': 'close'})
    
    def action_draft(self):
        self.depreciation_line_ids.unlink()
        self.write({'state': 'draft'})
    
    def compute_depreciation_board(self):
        for asset in self:
            # Remove existing draft lines
            asset.depreciation_line_ids.filtered(lambda x: not x.move_check).unlink()
            
            amount_to_depreciate = asset.original_value - asset.salvage_value
            depreciation_date = asset.first_depreciation_date or asset.date
            
            total_days = 0
            if asset.method_period == '1':
                total_days = 30
            elif asset.method_period == '3':
                total_days = 90
            else:
                total_days = 360
            
            depreciation_lines = []
            residual_amount = amount_to_depreciate
            
            for seq in range(1, asset.method_number + 1):
                if asset.method == 'linear':
                    amount = amount_to_depreciate / asset.method_number
                else:  # degressive
                    amount = residual_amount * asset.method_progress_factor
                
                # Prorata temporis for first line
                if seq == 1 and asset.prorata:
                    days = (depreciation_date.replace(day=1) + 
                           relativedelta(months=1) - depreciation_date).days
                    amount = (amount / total_days) * days
                
                residual_amount -= amount
                
                depreciation_lines.append({
                    'asset_id': asset.id,
                    'sequence': seq,
                    'name': f'{asset.name} - {seq}/{asset.method_number}',
                    'depreciation_date': depreciation_date,
                    'amount': amount,
                    'remaining_value': residual_amount,
                })
                
                # Next depreciation date
                if asset.method_period == '1':
                    depreciation_date += relativedelta(months=1)
                elif asset.method_period == '3':
                    depreciation_date += relativedelta(months=3)
                else:
                    depreciation_date += relativedelta(years=1)
            
            self.env['account.asset.depreciation.line'].create(depreciation_lines)
        
        return True


class AccountAssetDepreciationLine(models.Model):
    _name = 'account.asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'depreciation_date'

    asset_id = fields.Many2one('account.asset', 'Asset', required=True, 
                               ondelete='cascade')
    sequence = fields.Integer('Sequence')
    name = fields.Char('Depreciation Name', required=True)
    depreciation_date = fields.Date('Depreciation Date', required=True)
    amount = fields.Monetary('Amount', required=True, currency_field='currency_id')
    remaining_value = fields.Monetary('Remaining Value', currency_field='currency_id')
    
    move_id = fields.Many2one('account.move', 'Depreciation Entry')
    move_check = fields.Boolean('Posted', compute='_compute_move_check', store=True)
    
    currency_id = fields.Many2one('res.currency', related='asset_id.currency_id')
    company_id = fields.Many2one('res.company', related='asset_id.company_id')
    
    @api.depends('move_id.state')
    def _compute_move_check(self):
        for line in self:
            line.move_check = bool(line.move_id and line.move_id.state == 'posted')
    
    def create_move(self):
        for line in self:
            if line.move_check:
                continue
            
            asset = line.asset_id
            move_vals = {
                'date': line.depreciation_date,
                'journal_id': asset.journal_id.id,
                'ref': line.name,
                'line_ids': [
                    (0, 0, {
                        'name': line.name,
                        'account_id': asset.account_depreciation_expense_id.id,
                        'debit': line.amount if asset.asset_type == 'purchase' else 0.0,
                        'credit': 0.0 if asset.asset_type == 'purchase' else line.amount,
                        'partner_id': asset.partner_id.id,
                    }),
                    (0, 0, {
                        'name': line.name,
                        'account_id': asset.account_depreciation_id.id,
                        'debit': 0.0 if asset.asset_type == 'purchase' else line.amount,
                        'credit': line.amount if asset.asset_type == 'purchase' else 0.0,
                        'partner_id': asset.partner_id.id,
                    }),
                ],
            }
            
            move = self.env['account.move'].create(move_vals)
            line.write({'move_id': move.id})
            move.action_post()
        
        return True
