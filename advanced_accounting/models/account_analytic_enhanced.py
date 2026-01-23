# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountAnalyticAccountEnhanced(models.Model):
    _inherit = 'account.analytic.account'

    budget_ids = fields.One2many('account.budget.line', 'analytic_account_id', 
                                 'Budget Lines')
    cost_center_id = fields.Many2one('account.cost.center', 'Cost Center')
    
    total_budget = fields.Monetary('Total Budget', compute='_compute_budget_totals')
    total_spent = fields.Monetary('Total Spent', compute='_compute_budget_totals')
    budget_remaining = fields.Monetary('Budget Remaining', 
                                       compute='_compute_budget_totals')
    
    @api.depends('budget_ids.planned_amount', 'budget_ids.practical_amount')
    def _compute_budget_totals(self):
        for account in self:
            active_budgets = account.budget_ids.filtered(
                lambda b: b.budget_id.state in ['confirmed', 'approved', 'done']
            )
            account.total_budget = sum(active_budgets.mapped('planned_amount'))
            account.total_spent = sum(active_budgets.mapped('practical_amount'))
            account.budget_remaining = account.total_budget - account.total_spent


class AccountAnalyticLineEnhanced(models.Model):
    _inherit = 'account.analytic.line'

    cost_center_id = fields.Many2one('account.cost.center', 'Cost Center',
                                     compute='_compute_cost_center', store=True)
    budget_id = fields.Many2one('account.budget', 'Budget')
    
    @api.depends('account_id', 'account_id.cost_center_id')
    def _compute_cost_center(self):
        for line in self:
            if line.account_id and line.account_id.cost_center_id:
                line.cost_center_id = line.account_id.cost_center_id
