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
        ('cancel', 'Go Back and Continue Scanning'),
        ('partial', 'Process Partial Receipt (Create Backorder)'),
        ('force', 'Force Complete (Not Recommended)'),
    ], string='Action', default='cancel', required=True)
    
    partial_summary = fields.Html('Partial Summary', compute='_compute_partial_summary')
    scanned_sns_detail = fields.Html('Scanned Serial Numbers', compute='_compute_scanned_sns_detail')
    
    @api.depends('picking_id')
    def _compute_partial_summary(self):
        """Show detailed summary of what will be received vs backorder"""
        for wizard in self:
            if not wizard.picking_id:
                wizard.partial_summary = ''
                continue
            
            html = '<div class="mb-3">'
            html += '<h5><i class="fa fa-info-circle"/> Receipt Summary</h5>'
            html += '<table class="table table-sm table-bordered">'
            html += '<thead class="table-light">'
            html += '<tr>'
            html += '<th>Product</th>'
            html += '<th class="text-center">PO Qty</th>'
            html += '<th class="text-center" style="background-color: #d4edda;">✓ Will Receive</th>'
            html += '<th class="text-center" style="background-color: #fff3cd;">⏳ Backorder</th>'
            html += '</tr>'
            html += '</thead>'
            html += '<tbody>'
            
            for move in wizard.picking_id.move_ids_without_package:
                if move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type:
                    
                    # Count scanned SNs
                    scanned = len(wizard.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_id == move.product_id
                    ))
                    
                    total = int(move.product_uom_qty)
                    backorder = total - scanned
                    
                    html += '<tr>'
                    html += f'<td><strong>{move.product_id.display_name}</strong></td>'
                    html += f'<td class="text-center">{total}</td>'
                    html += f'<td class="text-center" style="color: green;"><strong>{scanned}</strong></td>'
                    html += f'<td class="text-center" style="color: orange;"><strong>{backorder}</strong></td>'
                    html += '</tr>'
            
            html += '</tbody>'
            html += '</table>'
            html += '</div>'
            
            wizard.partial_summary = html
    
    @api.depends('picking_id')
    def _compute_scanned_sns_detail(self):
        """Show list of scanned serial numbers grouped by product"""
        for wizard in self:
            if not wizard.picking_id or not wizard.picking_id.sn_move_ids:
                wizard.scanned_sns_detail = '<p class="text-muted">No serial numbers scanned yet.</p>'
                continue
            
            html = '<div class="mb-3">'
            html += '<h5><i class="fa fa-check-circle"/> Scanned Serial Numbers</h5>'
            
            # Group by product
            products = wizard.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.tracking == 'serial' and 
                         m.product_id.product_tmpl_id.sn_product_type
            )
            
            for move in products:
                scanned_sns = wizard.picking_id.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id == move.product_id
                )
                
                if not scanned_sns:
                    continue
                
                html += f'<div class="card mb-2">'
                html += f'<div class="card-header bg-light">'
                html += f'<strong>{move.product_id.display_name}</strong> '
                html += f'<span class="badge badge-success">{len(scanned_sns)} scanned</span>'
                html += f'</div>'
                html += f'<div class="card-body p-2">'
                html += f'<table class="table table-sm table-striped mb-0">'
                html += f'<thead><tr><th>Serial Number</th><th>Scanned By</th><th>Scan Time</th></tr></thead>'
                html += f'<tbody>'
                
                for sn_move in scanned_sns.sorted(lambda x: x.move_date):
                    html += f'<tr>'
                    html += f'<td><code>{sn_move.serial_number_name}</code></td>'
                    html += f'<td>{sn_move.user_id.name}</td>'
                    html += f'<td>{sn_move.move_date.strftime("%Y-%m-%d %H:%M:%S")}</td>'
                    html += f'</tr>'
                
                html += f'</tbody></table>'
                html += f'</div>'
                html += f'</div>'
            
            html += '</div>'
            
            wizard.scanned_sns_detail = html
    
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
        self.ensure_one()
        picking = self.picking_id
        
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f'[PARTIAL START] {picking.name}, state: {picking.state}')
        
        StockMoveLine = self.env['stock.move.line']
        
        # ==========================================
        # Step 1: Create move_lines for scanned SNs
        # ==========================================
        for move in picking.move_ids_without_package:
            if move.product_id.tracking != 'serial' or not move.product_id.product_tmpl_id.sn_product_type:
                continue
            
            scanned_lots = picking.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id == move.product_id
            ).mapped('serial_number_id')
            
            scanned_count = len(scanned_lots)
            
            _logger.info(f'[PARTIAL] {move.product_id.display_name}: scanned={scanned_count}/{move.product_uom_qty}')
            
            # Clear existing move_lines
            if move.move_line_ids:
                move.move_line_ids.unlink()
            
            if scanned_count == 0:
                continue
            
            # Create move_lines for scanned SNs
            for lot in scanned_lots:
                StockMoveLine.create({
                    'picking_id': picking.id,
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_id.uom_id.id,
                    'lot_id': lot.id,
                    'lot_name': lot.name,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'quantity': 1.0,
                    'company_id': picking.company_id.id,
                })
        
        # ==========================================
        # Step 2: Ensure picking state is assigned
        # ==========================================
        if picking.state not in ['assigned']:
            picking.state = 'assigned'
            _logger.info(f'[PARTIAL] Set state to assigned')
        
        # ==========================================
        # Step 3: Call _action_done() directly
        # This bypasses all button_validate checks
        # ==========================================
        _logger.info('[PARTIAL] Calling _action_done() directly')
        
        try:
            # This is the CORE method that does the actual transfer
            picking._action_done()
            
            _logger.info(f'[PARTIAL] _action_done() completed')
            _logger.info(f'[PARTIAL] Picking state: {picking.state}')
            
        except Exception as e:
            _logger.error(f'[PARTIAL] _action_done() failed: {str(e)}', exc_info=True)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('❌ Validation Failed'),
                    'message': _('Error: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        # ==========================================
        # Step 4: Check result
        # ==========================================
        
        # Refresh picking from DB
        picking.invalidate_recordset()
        
        _logger.info(f'[PARTIAL] Final picking state: {picking.state}')
        
        # Look for backorder
        backorder = self.env['stock.picking'].search([
            ('backorder_id', '=', picking.id)
        ], order='id desc', limit=1)
        
        if backorder:
            _logger.info(f'[PARTIAL] ✅ SUCCESS! Backorder created: {backorder.name}')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Partial Receipt Complete'),
                    'message': _(
                        '✓ Receipt: %s (Done)\n'
                        '✓ Backorder: %s (Ready)\n\n'
                        'Remaining items can be received later.'
                    ) % (picking.name, backorder.name),
                    'type': 'success',
                    'sticky': True,
                }
            }
        
        elif picking.state == 'done':
            _logger.info(f'[PARTIAL] ✅ Fully completed (no backorder needed)')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('✅ Receipt Complete'),
                    'message': _('All items received successfully!'),
                    'type': 'success',
                }
            }
        
        else:
            _logger.error(f'[PARTIAL] ❌ FAILED! State: {picking.state}')
            
            # Debug: Check moves
            for move in picking.move_ids:
                _logger.error(f'  Move: {move.product_id.display_name}, state: {move.state}, '
                            f'qty: {move.product_uom_qty}, lines: {len(move.move_line_ids)}')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('⚠️ Warning'),
                    'message': _(
                        'Validation completed but state is: %s\n'
                        'Please check the transfer manually.'
                    ) % picking.state,
                    'type': 'warning',
                    'sticky': True,
                }
            }

    def _force_validate(self):
        """Force validate without complete scan (not recommended)"""
        self.ensure_one()
        
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.warning(f'[FORCE VALIDATE] User forcing validation for {self.picking_id.name}')
        
        # Mark all moves as done with whatever was scanned
        for move in self.picking_id.move_ids_without_package:
            if move.product_id.tracking == 'serial' and move.product_id.product_tmpl_id.sn_product_type:
                # Set quantity based on scanned
                scanned = len(self.picking_id.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id == move.product_id
                ))
                
                if scanned > 0:
                    # Keep scanned items
                    for ml in move.move_line_ids:
                        if ml.lot_id:
                            ml.quantity = 1.0
                else:
                    # No scanned items, but force complete anyway (bad!)
                    _logger.warning(f'[FORCE] No SNs scanned for {move.product_id.display_name} but forcing complete!')
        
        # Validate without backorder check
        return self.picking_id.with_context(
            skip_sn_check=True,
            skip_backorder=True,
            skip_sms=True
        ).button_validate()