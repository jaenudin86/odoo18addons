# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta


class AccountPaymentFollowup(models.Model):
    _name = 'account.payment.followup'
    _description = 'Payment Follow-up'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    name = fields.Char('Follow-up Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    delay = fields.Integer('Days After Due Date', required=True,
                          help='Number of days after the due date to send this follow-up')
    
    description = fields.Html('Message', translate=True,
                             help='Message to be sent in the follow-up email')
    send_email = fields.Boolean('Send Email', default=True)
    send_letter = fields.Boolean('Send Letter')
    manual_action = fields.Boolean('Manual Action Required')
    manual_action_note = fields.Text('Manual Action Note')
    
    company_id = fields.Many2one('res.company', 'Company', 
                                 default=lambda self: self.env.company)


class AccountPaymentFollowupLine(models.Model):
    _name = 'account.payment.followup.line'
    _description = 'Payment Follow-up Line'
    _order = 'followup_date desc'

    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    followup_id = fields.Many2one('account.payment.followup', 'Follow-up Level')
    followup_date = fields.Date('Follow-up Date', default=fields.Date.today)
    
    move_line_ids = fields.Many2many('account.move.line', 
                                     'payment_followup_line_move_line_rel',
                                     'followup_line_id', 'move_line_id',
                                     'Journal Items')
    
    amount_due = fields.Monetary('Amount Due', compute='_compute_amount_due',
                                 currency_field='currency_id')
    company_id = fields.Many2one('res.company', 'Company', 
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    
    result = fields.Selection([
        ('letter', 'Letter Sent'),
        ('email', 'Email Sent'),
        ('phone', 'Phone Call'),
        ('visit', 'Visit'),
    ], 'Result')
    result_note = fields.Text('Result Note')
    
    @api.depends('move_line_ids.amount_residual')
    def _compute_amount_due(self):
        for line in self:
            line.amount_due = sum(line.move_line_ids.mapped('amount_residual'))
    
    def send_followup_email(self):
        self.ensure_one()
        template = self.env.ref('advanced_accounting.email_template_payment_followup', 
                               raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        self.write({'result': 'email'})
        return True


class ResPartner(models.Model):
    _inherit = 'res.partner'

    payment_followup_line_ids = fields.One2many('account.payment.followup.line',
                                                'partner_id', 'Follow-up History')
    last_followup_date = fields.Date('Last Follow-up Date',
                                     compute='_compute_last_followup_date')
    followup_level = fields.Many2one('account.payment.followup', 'Current Follow-up Level',
                                     compute='_compute_followup_level')
    
    @api.depends('payment_followup_line_ids.followup_date')
    def _compute_last_followup_date(self):
        for partner in self:
            if partner.payment_followup_line_ids:
                partner.last_followup_date = max(
                    partner.payment_followup_line_ids.mapped('followup_date')
                )
            else:
                partner.last_followup_date = False
    
    @api.depends('payment_followup_line_ids.followup_id')
    def _compute_followup_level(self):
        for partner in self:
            if partner.payment_followup_line_ids:
                latest_line = partner.payment_followup_line_ids.sorted(
                    'followup_date', reverse=True
                )[0]
                partner.followup_level = latest_line.followup_id
            else:
                partner.followup_level = False
