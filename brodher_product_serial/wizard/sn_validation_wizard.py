# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class BrodherSNValidationWizard(models.TransientModel):
    _name = 'brodher.sn.validation.wizard'
    _description = 'SN Validation Warning'
    
    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True, readonly=True)
    warning_message = fields.Text('Warning', readonly=True)
    can_create_backorder = fields.Boolean('Can Create Backorder', default=True, readonly=True)
    
    action_type = fields.Selection([
        ('cancel', 'Go Back and Scan More'),
        ('partial', 'Process Partial Receipt (Create Backorder)'),
        ('force', 'Force Complete (Not Recommended)'),
    ], string='Action', default='cancel', required=True)
    
    partial_summary = fields.Html('Partial Summary', compute='_compute_partial_summary')
    
    @api.depends('picking_id')
    def _compute_partial_summary(self):
        """Show what will be received vs what will go to backorder"""
        for wizard in self:
            if not wizard.picking_id:
                wizard.partial_summary = ''
                continue
            
            html = '<table class="table table-sm">'
            html += '<thead><tr><th>Product</th><th>Will Receive</th><th>Backorder</th><th>Total PO</th></tr></thead>'
            html += '<tbody>'
            
            for move in wizard.picking_id.move_ids_without_package:
                if move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type:
                    
                    scanned = len(wizard.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_id.product_tmpl_id == move.product_id.product_tmpl_id
                    ))
                    
                    total = int(move.product_uom_qty)
                    backorder = total - scanned
                    
                    html += '<tr>'
                    html += f'<td>{move.product_id.display_name}</td>'
                    html += f'<td><strong style="color: green;">{scanned}</strong></td>'
                    html += f'<td><strong style="color: orange;">{backorder}</strong></td>'
                    html += f'<td>{total}</td>'
                    html += '</tr>'
            
            html += '</tbody></table>'
            wizard.partial_summary = html
    
    def action_confirm(self):
        """Execute selected action"""
        self.ensure_one()
        
        if self.action_type == 'cancel':
            # Close wizard, return to picking
            return {'type': 'ir.actions.act_window_close'}
        
        elif self.action_type == 'partial':
            # Process partial receipt with backorder
            return self._process_partial_receipt()
        
        elif self.action_type == 'force':
            # Force validate (dangerous!)
            return self._force_validate()
    
    def _process_partial_receipt(self):
        """
        Process partial receipt - keep only scanned items
        """
        self.ensure_one()
        picking = self.picking_id
        
        _logger.info(f'[PARTIAL] Processing partial receipt for {picking.name}')
        
        # For each move, keep only scanned move_lines
        for move in picking.move_ids_without_package:
            if move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type:
                
                # Get scanned SNs for this product
                scanned_sns = picking.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id == move.product_id
                ).mapped('serial_number_id')
                
                scanned_count = len(scanned_sns)
                demand = int(move.product_uom_qty)
                
                _logger.info(f'[PARTIAL] {move.product_id.display_name}: {scanned_count}/{demand} scanned')
                
                if scanned_count > 0 and scanned_count < demand:
                    # Delete move_lines that are NOT in scanned list
                    for ml in move.move_line_ids:
                        if ml.lot_id and ml.lot_id not in scanned_sns:
                            _logger.info(f'[PARTIAL] Removing unscanned SN: {ml.lot_id.name}')
                            ml.unlink()
                    
                    # Ensure all move_lines for scanned SNs have quantity = 1
                    for ml in move.move_line_ids:
                        if ml.lot_id:
                            ml.quantity = 1.0
                    
                    _logger.info(f'[PARTIAL] Move lines after cleanup: {len(move.move_line_ids)}')
        
        # Now validate - Odoo will create backorder for remaining qty
        return picking.with_context(
            skip_sms=True,
            cancel_backorder=False  # Allow backorder creation
        ).button_validate()
    
    def _force_validate(self):
        """Force validate without complete scan"""
        self.ensure_one()
        
        # Mark all move_lines as done
        for move in self.picking_id.move_ids_without_package:
            move.quantity_done = move.product_uom_qty
        
        # Validate without backorder
        return self.picking_id.with_context(
            skip_backorder=True,
            skip_sms=True
        ).button_validate()