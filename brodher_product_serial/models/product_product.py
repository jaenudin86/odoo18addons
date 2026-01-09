# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    serial_number_ids = fields.One2many(
        'stock.lot', 'product_id', string='Serial Numbers',
        domain=[('sn_type', '!=', False)]
    )
    
    serial_count = fields.Integer(
        string='Serial Numbers', compute='_compute_serial_count'
    )
    
    @api.depends('serial_number_ids')
    def _compute_serial_count(self):
        for record in self:
            record.serial_count = len(record.serial_number_ids.filtered(lambda sn: sn.sn_type))
    
    def action_generate_serial_numbers(self):
        self.ensure_one()
        return {
            'name': _('Generate Serial Numbers'),
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.product.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.id,
                'default_product_tmpl_id': self.product_tmpl_id.id,
                'default_sn_type': self.product_tmpl_id.sn_product_type,
            }
        }
    
    def action_view_serial_numbers(self):
        self.ensure_one()
        return {
            'name': _('Serial Numbers - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id), ('sn_type', '!=', False)],
        }