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
        Process partial receipt/transfer - manual state management
        Works for: incoming, outgoing, internal
        """
        self.ensure_one()
        picking = self.picking_id
        
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f'[PARTIAL] Start: {picking.name} (Type: {picking.picking_type_code})')
        
        StockMoveLine = self.env['stock.move.line']
        
        # ==========================================
        # Step 1: Analyze what needs to be done
        # ==========================================
        processing_data = []
        
        for move in picking.move_ids_without_package:
            if move.product_id.tracking != 'serial' or not move.product_id.product_tmpl_id.sn_product_type:
                continue
            
            scanned_lots = picking.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id == move.product_id
            ).mapped('serial_number_id')
            
            scanned_count = len(scanned_lots)
            demand = int(move.product_uom_qty)
            remaining = demand - scanned_count
            
            _logger.info(f'[PARTIAL] [{move.product_id.default_code}] {move.product_id.display_name}: scanned={scanned_count}, demand={demand}, remaining={remaining}')
            
            processing_data.append({
                'move': move,
                'product': move.product_id,
                'scanned_lots': scanned_lots,
                'scanned_count': scanned_count,
                'original_demand': demand,  # Store original demand
                'remaining': remaining,
                'needs_backorder': remaining > 0,
            })
        
        # Check if anything was scanned
        total_scanned = sum(item['scanned_count'] for item in processing_data)
        if total_scanned == 0:
            _logger.error('[PARTIAL] No items scanned! Cannot process.')
            raise UserError(_(
                '❌ No Items Scanned!\n\n'
                'At least some items must be scanned to process partial transfer.\n'
                'Please scan items or cancel the operation.'
            ))
        
        # ==========================================
        # Step 2: Create backorder picking FIRST (before modifying moves)
        # ==========================================
        backorder_picking = None
        needs_backorder = any(item['needs_backorder'] for item in processing_data)
        
        if needs_backorder:
            _logger.info('[PARTIAL] Creating backorder picking...')

            # Create empty backorder
            backorder_picking = picking.copy({
                'name': '/',
                'backorder_id': picking.id,
                'state': 'draft',
            })

            # Hapus semua moves & move_lines yang ikut ter-copy
            # (move_ids_without_package adalah computed field, tidak bisa di-clear via copy vals)
            backorder_picking.move_line_ids.unlink()
            backorder_picking.move_ids.unlink()

            # Create moves for backorder BEFORE modifying original
            for item in processing_data:
                if not item['needs_backorder']:
                    continue  # Skip complete items
                
                original_move = item['move']
                remaining = item['remaining']
                
                _logger.info(f'[PARTIAL] Creating backorder move: {item["product"].display_name} x {remaining}')
                
                # Copy original move to backorder
                original_move.copy({
                    'picking_id': backorder_picking.id,
                    'product_uom_qty': float(remaining),
                    'quantity': 0.0,  # Done qty harus 0, bukan remaining
                    'state': 'draft',
                    'move_line_ids': [],  # No move_lines in backorder yet
                })
            
            # Confirm backorder
            backorder_picking.action_confirm()
            
            # For internal transfer, assign stock
            if picking.picking_type_code == 'internal':
                backorder_picking.action_assign()
            
            _logger.info(f'[PARTIAL] ✓ Backorder created: {backorder_picking.name}')
        
        # ==========================================
        # Step 3: Process original picking
        # ==========================================
        for item in processing_data:
            move = item['move']
            scanned_lots = item['scanned_lots']
            scanned_count = item['scanned_count']
            
            # Clear existing move_lines
            if move.move_line_ids:
                move.move_line_ids.unlink()
            
            # CASE 1: Nothing scanned - cancel this move
            if scanned_count == 0:
                _logger.info(f'[PARTIAL] No scan for {item["product"].display_name} - canceling move')
                move.write({'state': 'cancel'})
                continue
            
            # CASE 2: Something scanned - create move_lines
            _logger.info(f'[PARTIAL] Creating {scanned_count} move_lines for {item["product"].display_name}')
            
            for lot in scanned_lots:
                StockMoveLine.create({
                    'picking_id': picking.id,
                    'move_id': move.id,
                    'product_id': item['product'].id,
                    'product_uom_id': item['product'].uom_id.id,
                    'lot_id': lot.id,
                    'lot_name': lot.name,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'quantity': 1.0,
                    'company_id': picking.company_id.id,
                })
            
            # Update move qty to scanned qty
            move.write({
                'product_uom_qty': float(scanned_count),
                'state': 'assigned',  # Make sure it's assigned before marking done
            })
            
            _logger.info(f'[PARTIAL] Updated move: {item["product"].display_name} qty={scanned_count}')
        
        # ==========================================
        # Step 4: Mark original picking as done
        # ==========================================
        _logger.info('[PARTIAL] Marking moves as done...')
        
        for item in processing_data:
            if item['scanned_count'] > 0:
                item['move'].write({'state': 'done'})
        
        picking.write({
            'state': 'done',
            'date_done': fields.Datetime.now(),
        })
        
        _logger.info(f'[PARTIAL] Picking {picking.name} → done')
        
        # ==========================================
        # Step 5: Update stock quants
        # ==========================================
        _logger.info('[PARTIAL] Updating stock quants...')
        
        for item in processing_data:
            if item['scanned_count'] == 0:
                continue
            
            move = item['move']
            
            for ml in move.move_line_ids:
                if not ml.lot_id:
                    continue
                
                dest_location = ml.location_dest_id
                
                # Increase destination (for internal locations)
                if dest_location.usage == 'internal':
                    quant = self.env['stock.quant'].search([
                        ('location_id', '=', dest_location.id),
                        ('product_id', '=', ml.product_id.id),
                        ('lot_id', '=', ml.lot_id.id),
                    ], limit=1)
                    
                    if quant:
                        quant.write({'quantity': quant.quantity + ml.quantity})
                    else:
                        self.env['stock.quant'].create({
                            'location_id': dest_location.id,
                            'product_id': ml.product_id.id,
                            'lot_id': ml.lot_id.id,
                            'quantity': ml.quantity,
                            'company_id': ml.company_id.id,
                        })
                    
                    _logger.info(f'[PARTIAL] Quant updated: {ml.lot_id.name} at {dest_location.name}')
                
                # Decrease source (for internal/outgoing)
                if picking.picking_type_code in ['internal', 'outgoing']:
                    source_quant = self.env['stock.quant'].search([
                        ('location_id', '=', ml.location_id.id),
                        ('product_id', '=', ml.product_id.id),
                        ('lot_id', '=', ml.lot_id.id),
                    ], limit=1)
                    
                    if source_quant:
                        source_quant.write({'quantity': source_quant.quantity - ml.quantity})
                        _logger.info(f'[PARTIAL] Quant decreased: {ml.lot_id.name} at {ml.location_id.name}')
        
        self.env.cr.commit()
        
        # ==========================================
        # Step 6: Success notification
        # ==========================================
        _logger.info('[PARTIAL] ✅ SUCCESS!')
        _logger.info(f'[PARTIAL]   Original: {picking.name} (state: {picking.state})')
        
        if backorder_picking:
            _logger.info(f'[PARTIAL]   Backorder: {backorder_picking.name} (state: {backorder_picking.state})')
            
            if picking.picking_type_code == 'internal':
                message = _(
                    'Transfer processed successfully!\n\n'
                    '✓ Completed: %s\n'
                    '✓ Backorder: %s\n\n'
                    '📦 Note: For internal transfer, scan SNs directly in backorder (no generation needed).'
                ) % (picking.name, backorder_picking.name)
            else:
                message = _(
                    'Receipt processed successfully!\n\n'
                    '✓ Completed: %s\n'
                    '✓ Backorder: %s\n\n'
                    'Remaining items can be received later.'
                ) % (picking.name, backorder_picking.name)
        else:
            message = _(
                'Transfer completed successfully!\n\n'
                '✓ All scanned items processed: %s'
            ) % picking.name
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Partial Transfer Complete'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }
    def _process_partial_receipt2(self):
        """
        Process partial receipt/transfer - manual state management
        Works for: incoming, outgoing, internal
        """
        self.ensure_one()
        picking = self.picking_id
        
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f'[PARTIAL] Start: {picking.name} (Type: {picking.picking_type_code})')
        
        StockMoveLine = self.env['stock.move.line']
        
        # ==========================================
        # Step 1: Create move_lines for scanned SNs
        # ==========================================
        moves_to_process = []
        moves_for_backorder = []
        
        for move in picking.move_ids_without_package:
            if move.product_id.tracking != 'serial' or not move.product_id.product_tmpl_id.sn_product_type:
                continue
            
            scanned_lots = picking.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id == move.product_id
            ).mapped('serial_number_id')
            
            scanned_count = len(scanned_lots)
            demand = int(move.product_uom_qty)
            
            _logger.info(f'[PARTIAL] [{move.product_id.default_code}] {move.product_id.display_name}: {scanned_count}/{demand}')
            
            # CASE 1: Nothing scanned - entire move goes to backorder
            if scanned_count == 0:
                _logger.info(f'[PARTIAL] No scan - entire qty ({demand}) → backorder')
                moves_for_backorder.append({
                    'move': move,
                    'qty': demand,
                })
                continue
            
            # CASE 2: Something scanned - create move_lines
            # Clear existing move_lines
            if move.move_line_ids:
                move.move_line_ids.unlink()
            
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
                _logger.info(f'[PARTIAL] Created move_line for SN: {lot.name}')
            
            # Track for processing
            moves_to_process.append({
                'move': move,
                'scanned': scanned_count,
            })
            
            # CASE 3: Partial scan - remaining goes to backorder
            remaining = demand - scanned_count
            if remaining > 0:
                _logger.info(f'[PARTIAL] Partial scan - remaining {remaining} → backorder')
                moves_for_backorder.append({
                    'move': move,
                    'qty': remaining,
                })
        
        # Check if anything was scanned
        if not moves_to_process:
            _logger.error('[PARTIAL] No items scanned! Cannot process.')
            raise UserError(_(
                '❌ No Items Scanned!\n\n'
                'At least some items must be scanned to process partial transfer.\n'
                'Please scan items or cancel the operation.'
            ))
        
        # ==========================================
        # Step 2: Create backorder picking (if needed)
        # ==========================================
        backorder_picking = None
        
        if moves_for_backorder:
            _logger.info(f'[PARTIAL] Creating backorder for {len(moves_for_backorder)} products...')
            
            # Create backorder picking
            backorder_picking = picking.copy({
                'name': '/',
                'move_ids_without_package': [],
                'move_line_ids': [],
                'backorder_id': picking.id,
                'state': 'draft',
            })
            
            # Create moves in backorder
            for item in moves_for_backorder:
                original_move = item['move']
                qty = item['qty']
                
                original_move.copy({
                    'picking_id': backorder_picking.id,
                    'product_uom_qty': float(qty),
                    'quantity': float(qty),
                    'state': 'draft',
                    'move_line_ids': [],
                })
                
                _logger.info(f'[PARTIAL] Backorder move: {original_move.product_id.display_name} x {qty}')
            
            # Confirm backorder
            backorder_picking.action_confirm()
            
            # For internal transfer, assign stock
            if picking.picking_type_code == 'internal':
                backorder_picking.action_assign()
            
            _logger.info(f'[PARTIAL] ✓ Backorder created: {backorder_picking.name}')
        
        # ==========================================
        # Step 3: Update original moves to scanned qty
        # ==========================================
        for item in moves_to_process:
            move = item['move']
            scanned = item['scanned']
            
            # Update move qty to scanned qty
            move.write({'product_uom_qty': float(scanned)})
            _logger.info(f'[PARTIAL] Updated move qty: {move.product_id.display_name} → {scanned}')
        
        # ==========================================
        # Step 4: Validate original picking
        # ==========================================
        _logger.info('[PARTIAL] Validating original picking...')
        
        # Mark moves as done
        for item in moves_to_process:
            move = item['move']
            move.write({'state': 'done'})
            _logger.info(f'[PARTIAL] Move {move.id} → done')
        
        # Mark picking as done
        picking.write({
            'state': 'done',
            'date_done': fields.Datetime.now(),
        })
        
        _logger.info(f'[PARTIAL] Picking {picking.name} → done')
        
        # ==========================================
        # Step 5: Update stock (quants)
        # ==========================================
        _logger.info('[PARTIAL] Updating stock quants...')
        
        for item in moves_to_process:
            move = item['move']
            
            # For each move_line, update quant
            for ml in move.move_line_ids:
                if ml.lot_id:
                    # Check destination location type
                    dest_location = ml.location_dest_id
                    
                    # Only update quants for internal locations
                    if dest_location.usage == 'internal':
                        # Find or create quant
                        quant = self.env['stock.quant'].search([
                            ('location_id', '=', dest_location.id),
                            ('product_id', '=', ml.product_id.id),
                            ('lot_id', '=', ml.lot_id.id),
                        ], limit=1)
                        
                        if quant:
                            quant.write({'quantity': quant.quantity + ml.quantity})
                            _logger.info(f'[PARTIAL] Updated quant: {ml.lot_id.name} at {dest_location.name}')
                        else:
                            self.env['stock.quant'].create({
                                'location_id': dest_location.id,
                                'product_id': ml.product_id.id,
                                'lot_id': ml.lot_id.id,
                                'quantity': ml.quantity,
                                'company_id': ml.company_id.id,
                            })
                            _logger.info(f'[PARTIAL] Created quant: {ml.lot_id.name} at {dest_location.name}')
                    
                    # Decrease from source location (for internal/outgoing)
                    if picking.picking_type_code in ['internal', 'outgoing']:
                        source_quant = self.env['stock.quant'].search([
                            ('location_id', '=', ml.location_id.id),
                            ('product_id', '=', ml.product_id.id),
                            ('lot_id', '=', ml.lot_id.id),
                        ], limit=1)
                        
                        if source_quant:
                            new_qty = source_quant.quantity - ml.quantity
                            source_quant.write({'quantity': new_qty})
                            _logger.info(f'[PARTIAL] Decreased quant: {ml.lot_id.name} at {ml.location_id.name} → {new_qty}')
        
        self.env.cr.commit()
        
        # ==========================================
        # Step 6: Success notification
        # ==========================================
        _logger.info(f'[PARTIAL] ✅ SUCCESS!')
        _logger.info(f'[PARTIAL]   Original: {picking.name} (state: {picking.state})')
        if backorder_picking:
            _logger.info(f'[PARTIAL]   Backorder: {backorder_picking.name} (state: {backorder_picking.state})')
        
        # Build notification message
        if backorder_picking:
            if picking.picking_type_code == 'internal':
                message = _(
                    'Transfer processed successfully!\n\n'
                    '✓ Completed: %s\n'
                    '✓ Backorder: %s\n\n'
                    '📦 Note: For internal transfer, scan SNs directly in backorder (no generation needed).'
                ) % (picking.name, backorder_picking.name)
            else:
                message = _(
                    'Receipt processed successfully!\n\n'
                    '✓ Completed: %s\n'
                    '✓ Backorder: %s\n\n'
                    'Remaining items can be received later.'
                ) % (picking.name, backorder_picking.name)
        else:
            message = _(
                'Transfer completed successfully!\n\n'
                '✓ All scanned items processed: %s'
            ) % picking.name
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Partial Transfer Complete'),
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }
    def _process_partial_receipt1(self):
        """
        Process partial receipt - manual state management
        """
        self.ensure_one()
        picking = self.picking_id
        
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f'[PARTIAL] Start: {picking.name}')
        
        StockMoveLine = self.env['stock.move.line']
        
        # ==========================================
        # Step 1: Create move_lines for scanned SNs
        # ==========================================
        moves_to_process = []
        
        for move in picking.move_ids_without_package:
            if move.product_id.tracking != 'serial' or not move.product_id.product_tmpl_id.sn_product_type:
                continue
            
            scanned_lots = picking.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id == move.product_id
            ).mapped('serial_number_id')
            
            scanned_count = len(scanned_lots)
            demand = move.product_uom_qty
            
            _logger.info(f'[PARTIAL] {move.product_id.display_name}: {scanned_count}/{demand}')
            
            # Clear move_lines
            if move.move_line_ids:
                move.move_line_ids.unlink()
            
            if scanned_count == 0:
                continue
            
            # Create move_lines
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
            
            if scanned_count < demand:
                # Partial - need backorder
                moves_to_process.append({
                    'move': move,
                    'scanned': scanned_count,
                    'remaining': demand - scanned_count
                })
        
        if not moves_to_process:
            # Nothing to process
            _logger.error('[PARTIAL] No moves to process!')
            return {'type': 'ir.actions.act_window_close'}
        
        # ==========================================
        # Step 2: Split moves (create backorder moves)
        # ==========================================
        _logger.info('[PARTIAL] Creating backorder...')
        
        backorder_moves = []
        
        for item in moves_to_process:
            move = item['move']
            remaining = item['remaining']
            
            _logger.info(f'[PARTIAL] Splitting {move.product_id.display_name}: keeping {item["scanned"]}, backorder {remaining}')
            
            # Update original move to scanned qty
            move.write({'product_uom_qty': float(item['scanned'])})
            
            # Create backorder move
            backorder_move = move.copy({
                'product_uom_qty': float(remaining),
                'move_line_ids': False,  # Clear move_lines
                'state': 'assigned',
            })
            
            backorder_moves.append(backorder_move)
            
            _logger.info(f'[PARTIAL] Created backorder move: {backorder_move.id}')
        
        # ==========================================
        # Step 3: Create backorder picking
        # ==========================================
        backorder_picking = picking.copy({
            'name': '/',
            'move_ids': [(6, 0, [m.id for m in backorder_moves])],
            'move_line_ids': False,
            'backorder_id': picking.id,
            'state': 'assigned',
        })
        
        _logger.info(f'[PARTIAL] Created backorder picking: {backorder_picking.name}')
        
        # Update backorder moves to point to new picking
        for move in backorder_moves:
            move.write({'picking_id': backorder_picking.id})
        
        # ==========================================
        # Step 4: Set original picking/moves to done
        # ==========================================
        _logger.info('[PARTIAL] Setting original picking to done...')
        
        # Mark all original moves as done
        for item in moves_to_process:
            move = item['move']
            move.write({'state': 'done'})
            _logger.info(f'[PARTIAL] Move {move.id} → done')
        
        # Mark picking as done
        picking.write({
            'state': 'done',
            'date_done': fields.Datetime.now(),
        })
        
        _logger.info(f'[PARTIAL] Picking {picking.name} → done')
        
        # ==========================================
        # Step 5: Update stock (quants)
        # ==========================================
        _logger.info('[PARTIAL] Updating stock...')
        
        for item in moves_to_process:
            move = item['move']
            
            # For each move_line, update quant
            for ml in move.move_line_ids:
                if ml.lot_id:
                    # Create or update quant
                    quant = self.env['stock.quant'].search([
                        ('location_id', '=', ml.location_dest_id.id),
                        ('product_id', '=', ml.product_id.id),
                        ('lot_id', '=', ml.lot_id.id),
                    ], limit=1)
                    
                    if quant:
                        quant.write({'quantity': quant.quantity + ml.quantity})
                        _logger.info(f'[PARTIAL] Updated quant for {ml.lot_id.name}')
                    else:
                        self.env['stock.quant'].create({
                            'location_id': ml.location_dest_id.id,
                            'product_id': ml.product_id.id,
                            'lot_id': ml.lot_id.id,
                            'quantity': ml.quantity,
                            'company_id': ml.company_id.id,
                        })
                        _logger.info(f'[PARTIAL] Created quant for {ml.lot_id.name}')
        
        self.env.cr.commit()
        
        # ==========================================
        # Step 6: Success!
        # ==========================================
        _logger.info(f'[PARTIAL] ✅ SUCCESS!')
        _logger.info(f'[PARTIAL]   Original: {picking.name} (state: {picking.state})')
        _logger.info(f'[PARTIAL]   Backorder: {backorder_picking.name} (state: {backorder_picking.state})')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Partial Receipt Complete'),
                'message': _(
                    'Receipt processed successfully!\n\n'
                    '✓ Completed: %s\n'
                    '✓ Backorder: %s\n\n'
                    'Remaining items can be received later.'
                ) % (picking.name, backorder_picking.name),
                'type': 'success',
                'sticky': True,
            }
        }
    def _force_validate1(self):
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
    def _force_validate(self):
        """
        Force validate without complete scan (not recommended)
        Will validate with scanned qty only, canceling unscanned items
        """
        self.ensure_one()
        picking = self.picking_id
        
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.warning(f'[FORCE VALIDATE] ⚠️ User forcing validation for {picking.name}')
        
        StockMoveLine = self.env['stock.move.line']
        
        # ==========================================
        # Process each move
        # ==========================================
        for move in picking.move_ids_without_package:
            # Skip non-SN products
            if move.product_id.tracking != 'serial' or not move.product_id.product_tmpl_id.sn_product_type:
                continue
            
            product = move.product_id
            demand = int(move.product_uom_qty)
            
            # Get scanned SNs
            scanned_lots = picking.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id == product
            ).mapped('serial_number_id')
            
            scanned_count = len(scanned_lots)
            
            _logger.warning(f'[FORCE] {product.display_name}: scanned {scanned_count}/{demand}')
            
            # Clear existing move_lines
            if move.move_line_ids:
                move.move_line_ids.unlink()
            
            # CASE 1: Something scanned - create move_lines and update qty
            if scanned_count > 0:
                # Create move_lines for scanned SNs
                for lot in scanned_lots:
                    StockMoveLine.create({
                        'picking_id': picking.id,
                        'move_id': move.id,
                        'product_id': product.id,
                        'product_uom_id': product.uom_id.id,
                        'lot_id': lot.id,
                        'lot_name': lot.name,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'quantity': 1.0,
                        'company_id': picking.company_id.id,
                    })
                
                # Update move qty to scanned qty
                move.write({
                    'product_uom_qty': float(scanned_count),
                    'state': 'assigned',
                })
                
                _logger.warning(f'[FORCE] Updated {product.display_name} qty: {demand} → {scanned_count}')
            
            # CASE 2: Nothing scanned - cancel this move
            else:
                _logger.warning(f'[FORCE] ⚠️ No SNs scanned for {product.display_name} - CANCELING move!')
                move.write({
                    'product_uom_qty': 0.0,
                    'state': 'cancel',
                })
        
        # ==========================================
        # Force validate
        # ==========================================
        _logger.warning('[FORCE] Proceeding with validation...')
        
        # Mark remaining moves as done
        for move in picking.move_ids_without_package:
            if move.state not in ['done', 'cancel']:
                if move.move_line_ids:
                    move.write({'state': 'done'})
                else:
                    move.write({'state': 'cancel'})
        
        # Mark picking as done
        picking.write({
            'state': 'done',
            'date_done': fields.Datetime.now(),
        })
        
        # Update quants manually
        self._update_quants_for_force(picking)
        
        self.env.cr.commit()
        
        _logger.warning(f'[FORCE] ✅ Picking {picking.name} force validated')
        
        # Show warning notification
        scanned_total = len(picking.sn_move_ids)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('⚠️ Force Validated'),
                'message': _(
                    'Transfer %s has been force validated.\n\n'
                    '⚠️ Warning: Only %s items were scanned.\n'
                    'Unscanned items have been canceled.\n\n'
                    'This action cannot be undone.'
                ) % (picking.name, scanned_total),
                'type': 'warning',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }

    def _update_quants_for_force(self, picking):
        """Update stock quants after force validation"""
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info('[FORCE] Updating stock quants...')
        
        for move in picking.move_ids_without_package:
            if move.state != 'done':
                continue
            
            for ml in move.move_line_ids:
                if not ml.lot_id:
                    continue
                
                dest_location = ml.location_dest_id
                
                # Increase destination (internal locations only)
                if dest_location.usage == 'internal':
                    quant = self.env['stock.quant'].search([
                        ('location_id', '=', dest_location.id),
                        ('product_id', '=', ml.product_id.id),
                        ('lot_id', '=', ml.lot_id.id),
                    ], limit=1)
                    
                    if quant:
                        quant.write({'quantity': quant.quantity + ml.quantity})
                    else:
                        self.env['stock.quant'].create({
                            'location_id': dest_location.id,
                            'product_id': ml.product_id.id,
                            'lot_id': ml.lot_id.id,
                            'quantity': ml.quantity,
                            'company_id': ml.company_id.id,
                        })
                    
                    _logger.info(f'[FORCE] Quant updated: {ml.lot_id.name} at {dest_location.name}')
                
                # Decrease source (for internal/outgoing)
                if picking.picking_type_code in ['internal', 'outgoing']:
                    source_quant = self.env['stock.quant'].search([
                        ('location_id', '=', ml.location_id.id),
                        ('product_id', '=', ml.product_id.id),
                        ('lot_id', '=', ml.lot_id.id),
                    ], limit=1)
                    
                    if source_quant:
                        new_qty = source_quant.quantity - ml.quantity
                        source_quant.write({'quantity': new_qty})
                        _logger.info(f'[FORCE] Quant decreased: {ml.lot_id.name} at {ml.location_id.name}')