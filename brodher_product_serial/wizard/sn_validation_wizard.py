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
        Process partial receipt and create backorder
        """
        self.ensure_one()
        picking = self.picking_id
        
        # Update move quantities based on scanned SNs
        for move in picking.move_ids_without_package:
            if move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type:
                
                # Count how many SNs were scanned for this product
                scanned_count = len(picking.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id.product_tmpl_id == move.product_id.product_tmpl_id
                ))
                
                original_qty = move.product_uom_qty
                
                if scanned_count > 0 and scanned_count < original_qty:
                    # Update quantity_done to scanned count
                    # This tells Odoo to only process scanned items
                    for ml in move.move_line_ids:
                        if ml.lot_id and ml.lot_id in picking.sn_move_ids.mapped('serial_number_id'):
                            ml.quantity = 1  # Confirm this line
                    
                    # Set move quantity_done
                    move.quantity_done = scanned_count
        
        # Now validate - Odoo will detect partial and offer backorder
        # We force it to create backorder
        return picking.with_context(
            skip_backorder=False,  # Force backorder prompt
            skip_sms=True
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