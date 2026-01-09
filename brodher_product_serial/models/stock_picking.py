# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    sn_move_ids = fields.One2many('brodher.sn.move', 'picking_id', string='SN Moves')
    scanned_sn_count = fields.Integer(string='Scanned SN', compute='_compute_scanned_sn_count')
    require_sn_scan = fields.Boolean(string='Require SN', compute='_compute_require_sn_scan')
    
    @api.depends('sn_move_ids')
    def _compute_scanned_sn_count(self):
        for picking in self:
            picking.scanned_sn_count = len(picking.sn_move_ids)
    
    @api.depends('move_ids_without_package')
    def _compute_require_sn_scan(self):
        for picking in self:
            picking.require_sn_scan = any(
                move.product_id.product_tmpl_id.sn_product_type
                for move in picking.move_ids_without_package
            )
    
    def action_scan_serial_number(self):
        self.ensure_one()
        move_type = 'internal'
        if self.picking_type_code == 'incoming':
            move_type = 'in'
        elif self.picking_type_code == 'outgoing':
            move_type = 'out'
        
        return {
            'name': _('Scan Serial Number - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_move_type': move_type,
                'default_location_src_id': self.location_id.id,
                'default_location_dest_id': self.location_dest_id.id,
            }
        }
    
    def action_view_sn_moves(self):
        self.ensure_one()
        return {
            'name': _('Serial Number Moves - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.sn.move',
            'view_mode': 'tree,form',
            'domain': [('picking_id', '=', self.id)],
        }
    
    def _check_sn_scan_completion(self):
        self.ensure_one()
        if not self.require_sn_scan:
            return True, None
        
        for move in self.move_ids_without_package:
            product_tmpl = move.product_id.product_tmpl_id
            if not product_tmpl.sn_product_type:
                continue
            
            scanned_count = len(self.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id.product_tmpl_id == product_tmpl
            ))
            required_qty = int(move.product_uom_qty)
            
            if scanned_count < required_qty:
                return False, _(
                    'Product "%s" requires %d serial numbers, but only %d scanned!'
                ) % (product_tmpl.name, required_qty, scanned_count)
        
        return True, None
    
    def button_validate(self):
        for picking in self:
            if picking.require_sn_scan:
                is_complete, error_msg = picking._check_sn_scan_completion()
                if not is_complete:
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'brodher.sn.validation.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_picking_id': picking.id,
                            'default_warning_message': error_msg,
                        }
                    }
        return super(StockPicking, self).button_validate()