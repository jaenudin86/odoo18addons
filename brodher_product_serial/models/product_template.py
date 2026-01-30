# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    sn_product_type = fields.Selection([
        ('M', 'Man'),
        ('W', 'Woman')
    ], string='Product Type', default='M')
    
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
        if not any(p.tracking == 'serial' for p in self.product_variant_ids):
            raise UserError(_(
                'Product must have tracking by Serial Number!\n\n'
                'Enable: Inventory Tab → Tracking → By Unique Serial Number'
            ))
        return {
            'name': _('Generate Serial Numbers'),
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.product.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_id': self.id,
                'default_sn_type': self.sn_product_type,
            }
        }
    
    def action_view_serial_numbers(self):
        self.ensure_one()
        return {
            'name': _('Serial Numbers - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.lot',
            'view_mode': 'tree,form',
            'domain': [
                ('product_id.product_tmpl_id', '=', self.id),
                ('sn_type', '!=', False)
            ],
        }