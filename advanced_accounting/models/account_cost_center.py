# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountCostCenter(models.Model):
    _name = 'account.cost.center'
    _description = 'Cost Center'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code, name'

    name = fields.Char('Cost Center Name', required=True, tracking=True)
    code = fields.Char('Cost Center Code', required=True, tracking=True)
    
    active = fields.Boolean('Active', default=True)
    
    parent_id = fields.Many2one('account.cost.center', 'Parent Cost Center',
                               domain="[('id', '!=', id)]")
    child_ids = fields.One2many('account.cost.center', 'parent_id', 
                               'Child Cost Centers')
    
    manager_id = fields.Many2one('res.users', 'Manager', tracking=True)
    company_id = fields.Many2one('res.company', 'Company', 
                                 default=lambda self: self.env.company)
    
    analytic_account_ids = fields.One2many('account.analytic.account', 
                                          'cost_center_id', 'Analytic Accounts')
    analytic_line_ids = fields.One2many('account.analytic.line', 
                                       'cost_center_id', 'Analytic Lines')
    
    total_cost = fields.Monetary('Total Cost', compute='_compute_totals',
                                currency_field='currency_id')
    total_revenue = fields.Monetary('Total Revenue', compute='_compute_totals',
                                   currency_field='currency_id')
    balance = fields.Monetary('Balance', compute='_compute_totals',
                             currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    
    note = fields.Text('Notes')
    
    @api.depends('analytic_line_ids.amount')
    def _compute_totals(self):
        for center in self:
            lines = center.analytic_line_ids
            center.total_cost = abs(sum(lines.filtered(lambda l: l.amount < 0).mapped('amount')))
            center.total_revenue = sum(lines.filtered(lambda l: l.amount > 0).mapped('amount'))
            center.balance = center.total_revenue - center.total_cost
    
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive cost centers.'))
    
    def name_get(self):
        result = []
        for center in self:
            name = f'[{center.code}] {center.name}' if center.code else center.name
            result.append((center.id, name))
        return result
