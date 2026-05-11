# -*- coding: utf-8 -*-
from odoo import models, fields

class WooSyncLog(models.Model):
    _name = 'woo.sync.log'
    _description = 'WooCommerce Sync Log'
    _order = 'create_date desc'

    backend_id = fields.Many2one('woo.backend', string='Backend', required=True)
    operation = fields.Selection([
        ('import', 'Import'),
        ('export', 'Export'),
    ], string='Operation')
    
    resource = fields.Selection([
        ('product', 'Product'),
        ('category', 'Category'),
        ('attribute', 'Attribute'),
        ('order', 'Order'),
        ('customer', 'Customer'),
        ('stock', 'Stock'),
    ], string='Resource')
    
    state = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('warning', 'Warning'),
    ], string='Status', default='success')
    
    message = fields.Text('Message')
    raw_response = fields.Text('Raw Response (JSON)')
