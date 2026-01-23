# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountBudgetWizard(models.TransientModel):
    _name = 'account.budget.wizard'
    _description = 'Budget Wizard'

    date_from = fields.Date('Start Date', required=True, default=fields.Date.today)
    date_to = fields.Date('End Date', required=True)
    analytic_account_ids = fields.Many2many('account.analytic.account', 
                                           'budget_wizard_analytic_rel',
                                           string='Analytic Accounts')
    
    def action_generate_budget(self):
        """Generate budget lines based on selected criteria"""
        self.ensure_one()
        
        budget_id = self.env.context.get('active_id')
        if not budget_id:
            return
        
        budget = self.env['account.budget'].browse(budget_id)
        
        # Remove existing draft lines
        budget.budget_line_ids.unlink()
        
        # Create new budget lines
        for analytic_account in self.analytic_account_ids:
            self.env['account.budget.line'].create({
                'budget_id': budget.id,
                'analytic_account_id': analytic_account.id,
                'planned_amount': 0.0,
            })
        
        return {'type': 'ir.actions.act_window_close'}
