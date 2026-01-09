# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

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
    product_tmpl_id = fields.Many2one(
        related='serial_number_id.product_id.product_tmpl_id',
        string='Product', store=True
    )