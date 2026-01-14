# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class BrodherSNValidationWizard(models.TransientModel):
    _name = 'brodher.sn.validation.wizard'
    _description = 'SN Validation Warning'
    
    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True)
    warning_message = fields.Text('Warning', readonly=True)
    can_create_backorder = fields.Boolean('Can Create Backorder', default=False)
    
    action_type = fields.Selection([
        ('cancel', 'Go Back and Scan More'),
        ('force', 'Force Validate (Not Recommended)'),
        ('backorder', 'Create Backorder for Remaining Items'),
    ], string='Action', default='cancel', required=True)
    
    def action_confirm(self):
        """Execute selected action"""
        self.ensure_one()
        
        if self.action_type == 'cancel':
            # Just close wizard, return to picking
            return {'type': 'ir.actions.act_window_close'}
        
        elif self.action_type == 'backorder':
            # Create backorder and validate partial
            return self._create_backorder_and_validate()
        
        elif self.action_type == 'force':
            # Force validate without complete scan (dangerous!)
            return self.picking_id.with_context(skip_sn_check=True).button_validate()
    
    def _create_backorder_and_validate(self):
        """
        Create backorder for unscanned items and validate current picking
        """
        self.ensure_one()
        picking = self.picking_id
        
        # For each move with incomplete scan, split the move
        for move in picking.move_ids_without_package:
            if move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type:
                
                # Count scanned
                scanned_count = len(picking.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id.product_tmpl_id == move.product_id.product_tmpl_id
                ))
                
                required_qty = int(move.product_uom_qty)
                
                if scanned_count < required_qty:
                    # Update current move to scanned quantity
                    remaining_qty = required_qty - scanned_count
                    
                    # Split move: keep scanned in current, move rest to backorder
                    if scanned_count > 0:
                        move.product_uom_qty = scanned_count
                    
                    # Odoo will auto-create backorder for remaining
        
        # Now validate - Odoo will prompt for backorder creation
        return picking.button_validate()