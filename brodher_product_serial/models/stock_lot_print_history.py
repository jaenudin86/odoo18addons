# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockLotPrintHistory(models.Model):
    _name = 'stock.lot.print.history'
    _description = 'Serial Number Print History'
    _order = 'print_date desc'
    
    lot_id = fields.Many2one('stock.lot', 'Serial Number', required=True, ondelete='cascade')
    print_date = fields.Datetime('Tanggal Cetak', required=True, default=fields.Datetime.now)
    print_user = fields.Many2one('res.users', 'Dicetak Oleh', required=True, default=lambda self: self.env.user)
    print_count_at_time = fields.Integer('Print Ke-', required=True)
    picking_id = fields.Many2one('stock.picking', 'Transfer', ondelete='set null')
    notes = fields.Text('Catatan')