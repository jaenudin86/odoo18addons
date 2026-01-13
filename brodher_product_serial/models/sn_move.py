# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, exceptions

class BrodherSNMove(models.Model):
    _name = 'brodher.sn.move'
    _description = 'Serial Number Movement'
    _order = 'move_date desc'
    
    serial_number_id = fields.Many2one('stock.lot', string='Serial Number', required=True, ondelete='cascade')
    serial_number_name = fields.Char(related='serial_number_id.name', string='SN', store=True)
    
    move_type = fields.Selection([
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('internal', 'Internal Transfer')
    ], string='Move Type', required=True)
    
    location_src_id = fields.Many2one('stock.location', string='Source Location')
    location_dest_id = fields.Many2one('stock.location', string='Destination Location')
    move_date = fields.Datetime(string='Move Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    notes = fields.Text(string='Notes')
    picking_id = fields.Many2one('stock.picking', string='Stock Picking')
    
    # Related fields
    product_tmpl_id = fields.Many2one(
        related='serial_number_id.product_id.product_tmpl_id',
        string='Product Template', 
        store=True
    )
    
    # ADD THIS - Product Variant field
    product_id = fields.Many2one(
        related='serial_number_id.product_id',
        string='Product',
        store=True,
        readonly=True
    )
    
    # ADD THIS - For better display
    scanned_by = fields.Many2one(
        'res.users',
        string='Scanned By',
        related='user_id',
        store=True
    )
    
    scan_date = fields.Datetime(
        string='Scan Date',
        related='move_date',
        store=True
    )
    
    _sql_constraints = [
        ('unique_sn_per_picking', 
         'unique(serial_number_id, picking_id)', 
         'This Serial Number has already been scanned in this picking!'),
    ]
    
    @api.constrains('serial_number_id', 'move_type', 'picking_id')
    def _check_duplicate_incoming(self):
        """Prevent duplicate incoming for same SN"""
        for record in self:
            if record.move_type == 'in' and record.picking_id.state == 'done':
                # Check if this SN already received in another DONE picking
                existing = self.search([
                    ('serial_number_id', '=', record.serial_number_id.id),
                    ('move_type', '=', 'in'),
                    ('picking_id', '!=', record.picking_id.id),
                    ('picking_id.state', '=', 'done'),
                    ('id', '!=', record.id)
                ], limit=1)
                
                if existing:
                    raise exceptions.ValidationError(_(
                        'Serial Number %s has already been received!\n\n'
                        'Previous Receipt: %s\n'
                        'Date: %s\n'
                        'User: %s'
                    ) % (
                        record.serial_number_id.name,
                        existing.picking_id.name,
                        existing.move_date.strftime('%Y-%m-%d %H:%M'),
                        existing.user_id.name
                    ))