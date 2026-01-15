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
            """
            Process partial receipt with forced state management
            """
            self.ensure_one()
            picking = self.picking_id
            
            import logging
            _logger = logging.getLogger(__name__)
            
            _logger.info(f'[PARTIAL] Start: {picking.name}, state: {picking.state}')
            
            StockMoveLine = self.env['stock.move.line']
            
            # ==========================================
            # Step 1: Create move_lines
            # ==========================================
            for move in picking.move_ids_without_package:
                if move.product_id.tracking != 'serial' or not move.product_id.product_tmpl_id.sn_product_type:
                    continue
                
                _logger.info(f'[PARTIAL] Processing move: {move.product_id.display_name}, state: {move.state}')
                
                scanned_lots = picking.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id.product_id == move.product_id
                ).mapped('serial_number_id')
                
                scanned_count = len(scanned_lots)
                _logger.info(f'[PARTIAL] Scanned: {scanned_count}/{move.product_uom_qty}')
                
                # Clear move_lines
                if move.move_line_ids:
                    _logger.info(f'[PARTIAL] Deleting {len(move.move_line_ids)} existing move_lines')
                    move.move_line_ids.unlink()
                
                if scanned_count == 0:
                    _logger.info(f'[PARTIAL] No scanned items, skipping')
                    continue
                
                # Create move_lines
                for lot in scanned_lots:
                    ml = StockMoveLine.create({
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
                    _logger.info(f'[PARTIAL] Created move_line: {ml.id} for {lot.name}')
                
                # ==========================================
                # CRITICAL: Force move to 'assigned' state
                # ==========================================
                if move.state != 'assigned':
                    _logger.info(f'[PARTIAL] Forcing move state: {move.state} → assigned')
                    move.write({'state': 'assigned'})
            
            # ==========================================
            # Step 2: Force picking state
            # ==========================================
            if picking.state != 'assigned':
                _logger.info(f'[PARTIAL] Forcing picking state: {picking.state} → assigned')
                picking.write({'state': 'assigned'})
            
            # ==========================================
            # Step 3: Verify all moves are assigned
            # ==========================================
            _logger.info('[PARTIAL] Pre-validation check:')
            for move in picking.move_ids:
                _logger.info(f'  Move: {move.product_id.display_name}')
                _logger.info(f'    State: {move.state}')
                _logger.info(f'    Qty: {move.product_uom_qty}')
                _logger.info(f'    Move lines: {len(move.move_line_ids)}')
                _logger.info(f'    Move line qty: {sum(move.move_line_ids.mapped("quantity"))}')
            
            # ==========================================
            # Step 4: Commit changes before _action_done
            # ==========================================
            self.env.cr.commit()
            _logger.info('[PARTIAL] Changes committed')
            
            # ==========================================
            # Step 5: Call _action_done()
            # ==========================================
            _logger.info('[PARTIAL] Calling _action_done()')
            
            try:
                result = picking._action_done()
                _logger.info(f'[PARTIAL] _action_done() returned: {result}')
                
            except Exception as e:
                _logger.error(f'[PARTIAL] _action_done() exception: {str(e)}', exc_info=True)
                
                # Rollback
                self.env.cr.rollback()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('❌ Error'),
                        'message': _('Failed: %s') % str(e),
                        'type': 'danger',
                        'sticky': True,
                    }
                }
            
            # ==========================================
            # Step 6: Check result
            # ==========================================
            self.env.cr.commit()
            picking.invalidate_recordset()
            
            _logger.info('[PARTIAL] Post-validation check:')
            _logger.info(f'  Picking state: {picking.state}')
            
            for move in picking.move_ids:
                _logger.info(f'  Move: {move.product_id.display_name}, state: {move.state}')
            
            # Look for backorder
            backorder = self.env['stock.picking'].search([
                ('backorder_id', '=', picking.id)
            ], order='id desc', limit=1)
            
            if backorder:
                _logger.info(f'[PARTIAL] ✅ SUCCESS! Backorder: {backorder.name}')
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('✅ Partial Receipt Complete'),
                        'message': _(
                            '✓ Receipt: %s (Done)\n'
                            '✓ Backorder: %s (Ready)\n\n'
                            'You can receive remaining items later.'
                        ) % (picking.name, backorder.name),
                        'type': 'success',
                        'sticky': True,
                    }
                }
            
            elif picking.state == 'done':
                _logger.info(f'[PARTIAL] ✅ Fully complete')
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('✅ Complete'),
                        'message': _('All items received!'),
                        'type': 'success',
                    }
                }
            
            else:
                _logger.error(f'[PARTIAL] ❌ FAILED! State: {picking.state}')
                
                # Try to find what's blocking
                for move in picking.move_ids:
                    if move.state != 'done':
                        _logger.error(f'  Blocking move: {move.product_id.display_name}, state: {move.state}')
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('⚠️ Warning'),
                        'message': _(
                            'Validation incomplete.\n'
                            'State: %s\n\n'
                            'Check logs for details.'
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