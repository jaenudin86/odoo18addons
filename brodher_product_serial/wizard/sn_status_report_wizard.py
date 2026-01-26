# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SNStatusReportWizard(models.TransientModel):
    _name = 'brodher.sn.status.report.wizard'
    _description = 'SN Status Report Wizard'
    
    date_from = fields.Date('From Date')
    date_to = fields.Date('To Date', default=fields.Date.today)
    
    product_ids = fields.Many2many('product.product', string='Products')
    sn_status = fields.Selection([
        ('all', 'All Status'),
        ('available', 'Available (Generated)'),
        ('used', 'Used (In Stock)'),
        ('reserved', 'Reserved (Shipped)'),
        ('sold', 'Sold'),
    ], string='Filter by Status', default='all')
    
    sn_type = fields.Selection([
        ('all', 'All Types'),
        ('M', 'Man'),
        ('W', 'Woman'),
    ], string='Filter by Type', default='all')
    
    def action_print_report(self):
        """Generate PDF report"""
        self.ensure_one()
        
        # Build domain
        domain = [('sn_type', '!=', False)]
        
        if self.date_from:
            domain.append(('sn_generated_date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('sn_generated_date', '<=', self.date_to))
        
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        if self.sn_status != 'all':
            domain.append(('sn_status', '=', self.sn_status))
        
        if self.sn_type != 'all':
            domain.append(('sn_type', '=', self.sn_type))
        
        # Get serial numbers
        serial_numbers = self.env['stock.lot'].search(domain, order='name')
        
        if not serial_numbers:
            raise UserError(_('No serial numbers found with the selected criteria!'))
        
        # Generate report
        return self.env.ref('brodher_product_serial.action_report_sn_status').report_action(serial_numbers)
    
    def action_view_list(self):
        """View list instead of PDF"""
        self.ensure_one()
        
        # Build domain (same as print)
        domain = [('sn_type', '!=', False)]
        
        if self.date_from:
            domain.append(('sn_generated_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('sn_generated_date', '<=', self.date_to))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.sn_status != 'all':
            domain.append(('sn_status', '=', self.sn_status))
        if self.sn_type != 'all':
            domain.append(('sn_type', '=', self.sn_type))
        
        return {
            'name': _('Serial Numbers'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'group_by': 'sn_status'},
        }