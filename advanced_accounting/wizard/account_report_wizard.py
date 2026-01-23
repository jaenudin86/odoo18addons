# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountReportWizard(models.TransientModel):
    _name = 'account.report.wizard'
    _description = 'Account Report Wizard'

    date_from = fields.Date('Start Date', required=True, default=fields.Date.today)
    date_to = fields.Date('End Date', required=True, default=fields.Date.today)
    report_type = fields.Selection([
        ('budget', 'Budget Report'),
        ('asset', 'Asset Report'),
        ('cost_center', 'Cost Center Report'),
    ], string='Report Type', required=True, default='budget')
    
    company_id = fields.Many2one('res.company', 'Company', 
                                 default=lambda self: self.env.company)
    
    def action_print_report(self):
        """Print selected report"""
        self.ensure_one()
        
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'report_type': self.report_type,
            'company_id': self.company_id.id,
        }
        
        return self.env.ref('advanced_accounting.action_report_accounting').report_action(
            self, data=data
        )
