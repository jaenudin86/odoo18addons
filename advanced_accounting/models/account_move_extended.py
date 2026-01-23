# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    approval_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', string='Approval Status', tracking=True)
    
    approved_by = fields.Many2one('res.users', 'Approved By', readonly=True)
    approved_date = fields.Datetime('Approved Date', readonly=True)
    rejected_by = fields.Many2one('res.users', 'Rejected By', readonly=True)
    rejected_date = fields.Datetime('Rejected Date', readonly=True)
    rejection_reason = fields.Text('Rejection Reason')
    
    budget_warning = fields.Boolean('Budget Warning', compute='_compute_budget_warning')
    budget_warning_message = fields.Text('Budget Warning Message', 
                                         compute='_compute_budget_warning')
    
    cost_center_id = fields.Many2one('account.cost.center', 'Cost Center')
    
    @api.depends('line_ids.analytic_distribution')
    def _compute_budget_warning(self):
        for move in self:
            warning = False
            message = ""
            
            for line in move.line_ids.filtered(lambda l: l.analytic_distribution):
                for analytic_account_id in line.analytic_distribution.keys():
                    analytic_account = self.env['account.analytic.account'].browse(
                        int(analytic_account_id)
                    )
                    
                    if analytic_account.total_budget > 0:
                        if analytic_account.total_spent + abs(line.balance) > analytic_account.total_budget:
                            warning = True
                            message += f"\n- {analytic_account.name}: Budget exceeded!"
            
            move.budget_warning = warning
            move.budget_warning_message = message if warning else ""
    
    def action_request_approval(self):
        self.write({'approval_state': 'pending'})
    
    def action_approve(self):
        self.write({
            'approval_state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
    
    def action_reject(self):
        return {
            'name': _('Reject Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_move_id': self.id},
        }


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cost_center_id = fields.Many2one('account.cost.center', 'Cost Center',
                                     related='move_id.cost_center_id', store=True)
