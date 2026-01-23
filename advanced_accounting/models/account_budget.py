# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountBudget(models.Model):
    _name = 'account.budget'
    _description = 'Budget Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char('Budget Name', required=True, tracking=True)
    code = fields.Char('Budget Code', tracking=True)
    date_from = fields.Date('Start Date', required=True, tracking=True)
    date_to = fields.Date('End Date', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True)
    
    company_id = fields.Many2one('res.company', 'Company', 
                                 default=lambda self: self.env.company)
    budget_line_ids = fields.One2many('account.budget.line', 'budget_id', 
                                      'Budget Lines')
    
    total_planned = fields.Monetary('Total Planned Amount', 
                                    compute='_compute_totals', store=True)
    total_practical = fields.Monetary('Total Practical Amount', 
                                      compute='_compute_totals', store=True)
    total_percentage = fields.Float('Total Achievement %', 
                                    compute='_compute_totals', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    note = fields.Text('Notes')
    
    @api.depends('budget_line_ids.planned_amount', 'budget_line_ids.practical_amount')
    def _compute_totals(self):
        for budget in self:
            budget.total_planned = sum(budget.budget_line_ids.mapped('planned_amount'))
            budget.total_practical = sum(budget.budget_line_ids.mapped('practical_amount'))
            if budget.total_planned:
                budget.total_percentage = (budget.total_practical / budget.total_planned) * 100
            else:
                budget.total_percentage = 0.0
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for budget in self:
            if budget.date_from and budget.date_to and budget.date_from > budget.date_to:
                raise ValidationError(_('Start date must be before end date.'))
    
    def action_confirm(self):
        self.write({'state': 'confirmed'})
    
    def action_approve(self):
        self.write({'state': 'approved'})
    
    def action_done(self):
        self.write({'state': 'done'})
    
    def action_cancel(self):
        self.write({'state': 'cancelled'})
    
    def action_draft(self):
        self.write({'state': 'draft'})


class AccountBudgetLine(models.Model):
    _name = 'account.budget.line'
    _description = 'Budget Line'
    _order = 'analytic_account_id'

    budget_id = fields.Many2one('account.budget', 'Budget', ondelete='cascade', 
                                required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 
                                          'Analytic Account', required=True)
    general_account_id = fields.Many2one('account.account', 'General Account')
    
    date_from = fields.Date('Start Date', related='budget_id.date_from', store=True)
    date_to = fields.Date('End Date', related='budget_id.date_to', store=True)
    
    planned_amount = fields.Monetary('Planned Amount', required=True, 
                                     currency_field='currency_id')
    practical_amount = fields.Monetary('Practical Amount', 
                                       compute='_compute_practical_amount',
                                       currency_field='currency_id')
    theoretical_amount = fields.Monetary('Theoretical Amount', 
                                         compute='_compute_theoretical_amount',
                                         currency_field='currency_id')
    percentage = fields.Float('Achievement %', compute='_compute_percentage', 
                              store=True)
    
    currency_id = fields.Many2one('res.currency', related='budget_id.currency_id')
    company_id = fields.Many2one('res.company', related='budget_id.company_id')
    
    @api.depends('analytic_account_id', 'general_account_id', 'date_from', 'date_to')
    def _compute_practical_amount(self):
        for line in self:
            domain = [
                ('date', '>=', line.date_from),
                ('date', '<=', line.date_to),
                ('company_id', '=', line.company_id.id),
            ]
            
            if line.analytic_account_id:
                domain.append(('account_id', '=', line.analytic_account_id.id))
            
            if line.general_account_id:
                domain.append(('general_account_id', '=', line.general_account_id.id))
            
            analytic_lines = self.env['account.analytic.line'].search(domain)
            line.practical_amount = sum(analytic_lines.mapped('amount'))
    
    @api.depends('planned_amount', 'date_from', 'date_to')
    def _compute_theoretical_amount(self):
        today = fields.Date.today()
        for line in self:
            if line.date_from and line.date_to:
                total_days = (line.date_to - line.date_from).days + 1
                if today < line.date_from:
                    elapsed_days = 0
                elif today > line.date_to:
                    elapsed_days = total_days
                else:
                    elapsed_days = (today - line.date_from).days + 1
                
                if total_days > 0:
                    line.theoretical_amount = (line.planned_amount * elapsed_days) / total_days
                else:
                    line.theoretical_amount = 0.0
            else:
                line.theoretical_amount = 0.0
    
    @api.depends('planned_amount', 'practical_amount')
    def _compute_percentage(self):
        for line in self:
            if line.planned_amount:
                line.percentage = (line.practical_amount / line.planned_amount) * 100
            else:
                line.percentage = 0.0
