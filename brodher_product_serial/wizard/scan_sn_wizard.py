# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ScanSNWizard(models.TransientModel):
    _name = 'brodher.scan.sn.wizard'
    _description = 'Scan Serial Number Wizard'
    
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', required=True)
    picking_name = fields.Char(related='picking_id.name', string='Picking')
    picking_type = fields.Selection(related='picking_id.picking_type_code', string='Type')
    
    input_method = fields.Selection([
        ('scan', 'Scan QR Code'),
        ('manual', 'Select Manually')
    ], string='Input Method', default='scan', required=True)
    
    scanned_sn = fields.Char(string='Scan Serial Number')
    serial_number_id = fields.Many2one('stock.lot', string='Select Serial Number', domain="[('id', 'in', available_sn_ids)]")
    available_sn_ids = fields.Many2many('stock.lot', compute='_compute_available_sn_ids', string='Available SNs')
    
    move_type = fields.Selection([
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('internal', 'Internal Transfer')
    ], string='Move Type', required=True, default='in')
    
    location_src_id = fields.Many2one('stock.location', string='From')
    location_dest_id = fields.Many2one('stock.location', string='To', required=True)
    notes = fields.Text(string='Notes')
    
    sn_info = fields.Html(string='Serial Number Info', compute='_compute_sn_info')
    total_scanned = fields.Integer(string='Total Scanned', compute='_compute_total_scanned')
    scanned_list = fields.Html(string='Scanned List', compute='_compute_scanned_list')
    expected_quantities = fields.Html(string='Expected Quantities', compute='_compute_expected_quantities')
    
    @api.depends('picking_id', 'move_type')
    def _compute_available_sn_ids(self):
        """Get available serial numbers dengan logika yang benar"""
        for wizard in self:
            if not wizard.picking_id:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # Get products with SN tracking
            products = wizard.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.tracking == 'serial' and m.product_id.product_tmpl_id.sn_product_type
            ).mapped('product_id')
            
            if not products:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # Build domain
            domain = [
                ('product_id', 'in', products.ids),
                ('sn_type', '!=', False)
            ]
            
            # LOGIKA BERBEDA PER MOVE TYPE
            if wizard.move_type == 'in':
                # ====================================
                # BARANG MASUK: Hanya SN yang BELUM PERNAH masuk gudang
                # ====================================
                
                # Get all SN IDs that sudah pernah masuk (status done)
                already_received_sn_ids = self.env['brodher.sn.move'].search([
                    ('move_type', '=', 'in'),
                    ('picking_id.state', '=', 'done')
                ]).mapped('serial_number_id.id')
                
                # EXCLUDE SN yang sudah pernah received
                if already_received_sn_ids:
                    domain.append(('id', 'not in', already_received_sn_ids))
                
                # Hanya yang belum pernah dipakai atau baru generate
                # (tidak peduli status, yang penting belum pernah masuk)
                
            elif wizard.move_type == 'out':
                # ====================================
                # BARANG KELUAR: Hanya SN yang ADA DI GUDANG (sudah masuk, belum keluar)
                # ====================================
                
                # Get SN yang SUDAH masuk gudang (status done)
                received_sn_ids = self.env['brodher.sn.move'].search([
                    ('move_type', '=', 'in'),
                    ('picking_id.state', '=', 'done')
                ]).mapped('serial_number_id.id')
                
                # Get SN yang SUDAH keluar gudang (status done)
                shipped_sn_ids = self.env['brodher.sn.move'].search([
                    ('move_type', '=', 'out'),
                    ('picking_id.state', '=', 'done')
                ]).mapped('serial_number_id.id')
                
                # SN di gudang = sudah masuk TAPI belum keluar
                available_in_warehouse = list(set(received_sn_ids) - set(shipped_sn_ids))
                
                if available_in_warehouse:
                    domain.append(('id', 'in', available_in_warehouse))
                else:
                    # Tidak ada stock di gudang
                    domain.append(('id', '=', False))
                
                # Status harus available
                domain.append(('sn_status', '=', 'available'))
                
            elif wizard.move_type == 'internal':
                # ====================================
                # TRANSFER INTERNAL: Yang ada di gudang sumber
                # ====================================
                
                # Similar logic dengan outgoing
                received_sn_ids = self.env['brodher.sn.move'].search([
                    ('move_type', '=', 'in'),
                    ('picking_id.state', '=', 'done')
                ]).mapped('serial_number_id.id')
                
                shipped_sn_ids = self.env['brodher.sn.move'].search([
                    ('move_type', '=', 'out'),
                    ('picking_id.state', '=', 'done')
                ]).mapped('serial_number_id.id')
                
                available_in_warehouse = list(set(received_sn_ids) - set(shipped_sn_ids))
                
                if available_in_warehouse:
                    domain.append(('id', 'in', available_in_warehouse))
                else:
                    domain.append(('id', '=', False))
                
                domain.append(('sn_status', 'in', ['available', 'reserved']))
            
            # EXCLUDE yang sudah di-scan di picking ini (belum done)
            already_scanned_this_picking = wizard.picking_id.sn_move_ids.mapped('serial_number_id.id')
            if already_scanned_this_picking:
                domain.append(('id', 'not in', already_scanned_this_picking))
            
            available_sns = self.env['stock.lot'].search(domain, order='name')
            wizard.available_sn_ids = [(6, 0, available_sns.ids)]
    @api.depends('picking_id')
    def _compute_total_scanned(self):
        for wizard in self:
            wizard.total_scanned = len(wizard.picking_id.sn_move_ids) if wizard.picking_id else 0
    
    @api.depends('picking_id')
    def _compute_expected_quantities(self):
        """Show expected vs scanned quantities"""
        for wizard in self:
            if wizard.picking_id:
                html = '<div style="margin: 10px 0;"><strong>Products in This Picking:</strong>'
                html += '<table class="table table-sm table-bordered" style="margin-top: 5px;">'
                html += '<thead><tr><th>Product</th><th>Tracking</th><th>Expected</th><th>Scanned</th><th>Status</th></tr></thead><tbody>'
                
                for move in wizard.picking_id.move_ids_without_package:
                    product_tmpl = move.product_id.product_tmpl_id
                    expected = int(move.product_uom_qty)
                    
                    # Check if has SN tracking
                    has_sn_tracking = move.product_id.tracking == 'serial' and product_tmpl.sn_product_type
                    
                    if has_sn_tracking:
                        # Product dengan SN tracking
                        scanned = len(wizard.picking_id.sn_move_ids.filtered(
                            lambda sm: sm.serial_number_id.product_id.product_tmpl_id == product_tmpl
                        ))
                        
                        if scanned >= expected:
                            status = '<span style="color: green;">✓ Complete</span>'
                            row_style = 'background: #d4edda;'
                        elif scanned > 0:
                            status = '<span style="color: orange;">◐ Partial</span>'
                            row_style = 'background: #fff3cd;'
                        else:
                            status = '<span style="color: red;">○ Pending</span>'
                            row_style = ''
                        
                        html += f'<tr style="{row_style}">'
                        html += f'<td>{product_tmpl.name}</td>'
                        html += f'<td><span class="badge badge-info">SN Tracking</span></td>'
                        html += f'<td class="text-center">{expected}</td>'
                        html += f'<td class="text-center"><strong>{scanned}</strong></td>'
                        html += f'<td class="text-center">{status}</td></tr>'
                    else:
                        # Product tanpa SN tracking
                        html += f'<tr style="background: #e9ecef;">'
                        html += f'<td>{product_tmpl.name}</td>'
                        html += f'<td><span class="badge badge-secondary">No SN</span></td>'
                        html += f'<td class="text-center">{expected}</td>'
                        html += f'<td class="text-center">-</td>'
                        html += f'<td class="text-center"><span style="color: gray;">No scan required</span></td></tr>'
                
                html += '</tbody></table></div>'
                wizard.expected_quantities = html
            else:
                wizard.expected_quantities = ''
    
    @api.depends('picking_id')
    def _compute_scanned_list(self):
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sn_move_ids:
                html = '<div style="max-height: 150px; overflow-y: auto; margin-top: 10px;">'
                html += '<strong>Recently Scanned:</strong><table class="table table-sm">'
                html += '<thead><tr><th>SN</th><th>Product</th><th>Time</th><th>User</th></tr></thead><tbody>'
                
                for move in wizard.picking_id.sn_move_ids.sorted(lambda m: m.move_date, reverse=True)[:10]:
                    html += f'<tr><td><code>{move.serial_number_name}</code></td>'
                    html += f'<td><small>{move.product_tmpl_id.name}</small></td>'
                    html += f'<td><small>{move.move_date.strftime("%H:%M:%S")}</small></td>'
                    html += f'<td><small>{move.user_id.name}</small></td></tr>'
                
                html += '</tbody></table></div>'
                wizard.scanned_list = html
            else:
                wizard.scanned_list = '<p class="text-muted"><em>No serial numbers scanned yet</em></p>'
    
    @api.depends('scanned_sn', 'serial_number_id', 'input_method')
    def _compute_sn_info(self):
        for wizard in self:
            sn = None
            if wizard.input_method == 'scan' and wizard.scanned_sn:
                sn = self.env['stock.lot'].search([('name', '=', wizard.scanned_sn), ('sn_type', '!=', False)], limit=1)
            elif wizard.input_method == 'manual' and wizard.serial_number_id:
                sn = wizard.serial_number_id
            
            if sn:
                # Check movement history
                received = self.env['brodher.sn.move'].search([
                    ('serial_number_id', '=', sn.id),
                    ('move_type', '=', 'in'),
                    ('picking_id.state', '=', 'done')
                ], limit=1)
                
                shipped = self.env['brodher.sn.move'].search([
                    ('serial_number_id', '=', sn.id),
                    ('move_type', '=', 'out'),
                    ('picking_id.state', '=', 'done')
                ], limit=1)
                
                # Determine stock status
                if received and not shipped:
                    stock_status = '<span style="color: green; font-weight: bold;">✓ IN STOCK</span>'
                    bg_color = '#d4edda'
                elif shipped:
                    stock_status = '<span style="color: red; font-weight: bold;">✗ SHIPPED OUT</span>'
                    bg_color = '#f8d7da'
                else:
                    stock_status = '<span style="color: orange; font-weight: bold;">○ NEVER RECEIVED</span>'
                    bg_color = '#fff3cd'
                
                # Build info table
                wizard.sn_info = f'''<div style="padding: 15px; background: {bg_color}; border-radius: 5px; border-left: 4px solid #28a745;">
                    <h4>Serial Number Info</h4>
                    <table class="table table-sm">
                    <tr><td><strong>SN:</strong></td><td><span style="font-family: monospace; font-size: 16px;">{sn.name}</span></td></tr>
                    <tr><td><strong>Product:</strong></td><td>{sn.product_id.name}</td></tr>
                    <tr><td><strong>Type:</strong></td><td>{'Man' if sn.sn_type == 'M' else 'Woman'}</td></tr>
                    <tr><td><strong>Stock Status:</strong></td><td>{stock_status}</td></tr>
                    <tr><td><strong>SN Status:</strong></td><td>{sn.sn_status.upper() if sn.sn_status else 'NEW'}</td></tr>
                    <tr><td><strong>QC:</strong></td><td>{'✓ Passed' if sn.qc_passed else '✗ Failed'}</td></tr>
                '''
                
                # Show received info
                if received:
                    wizard.sn_info += f'''<tr style="border-top: 2px solid #ddd;"><td><strong>Received:</strong></td>
                        <td>{received.picking_id.name}<br/>{received.move_date.strftime("%Y-%m-%d %H:%M")}</td></tr>'''
                
                # Show shipped info
                if shipped:
                    wizard.sn_info += f'''<tr><td><strong>Shipped:</strong></td>
                        <td>{shipped.picking_id.name}<br/>{shipped.move_date.strftime("%Y-%m-%d %H:%M")}</td></tr>'''
                
                wizard.sn_info += '</table></div>'
                
            elif wizard.input_method == 'scan' and wizard.scanned_sn:
                wizard.sn_info = f'''<div style="padding: 15px; background: #f8d7da; border-radius: 5px;">
                    <h4 style="color: #721c24;">✗ Serial Number Not Found!</h4>
                    <p>Serial number <strong>{wizard.scanned_sn}</strong> does not exist.</p></div>'''
            else:
                wizard.sn_info = '''<div style="padding: 15px; background: #e7f3ff; border-radius: 5px;">
                    <p><strong>📱 Ready to scan or select...</strong></p></div>'''
    @api.onchange('input_method')
    def _onchange_input_method(self):
        
        if self.input_method == 'scan':
            self.serial_number_id = False
        else:
            self.scanned_sn = False
    def action_confirm_scan(self):
        """Confirm scanned serial number with strict validation"""
        self.ensure_one()
        
        # Get SN
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan or enter serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn), ('sn_type', '!=', False)], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found in the system!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select a serial number!'))
            sn = self.serial_number_id
        
        # ========================================
        # VALIDATION BERDASARKAN MOVE TYPE
        # ========================================
        
        if self.move_type == 'in':
            # INCOMING: Cek jangan sampai double receive
            existing_in = self.env['brodher.sn.move'].search([
                ('serial_number_id', '=', sn.id),
                ('move_type', '=', 'in'),
                ('picking_id.state', '=', 'done')
            ], limit=1)
            
            if existing_in:
                raise UserError(_(
                    '❌ SERIAL NUMBER SUDAH MASUK GUDANG!\n\n'
                    '🔹 Serial Number: %s\n'
                    '🔹 Received in: %s\n'
                    '🔹 Date: %s\n'
                    '🔹 User: %s\n\n'
                    '⚠️ Serial number ini TIDAK BISA diterima lagi!'
                ) % (
                    sn.name,
                    existing_in.picking_id.name,
                    existing_in.move_date.strftime('%Y-%m-%d %H:%M:%S'),
                    existing_in.user_id.name
                ))
        
        elif self.move_type == 'out':
            # OUTGOING: Harus sudah masuk gudang dan belum keluar
            
            # Cek apakah sudah masuk gudang
            received = self.env['brodher.sn.move'].search([
                ('serial_number_id', '=', sn.id),
                ('move_type', '=', 'in'),
                ('picking_id.state', '=', 'done')
            ], limit=1)
            
            if not received:
                raise UserError(_(
                    '❌ SERIAL NUMBER BELUM MASUK GUDANG!\n\n'
                    '🔹 Serial Number: %s\n\n'
                    '⚠️ SN ini belum pernah diterima di gudang.\n'
                    'Hanya SN yang sudah ada di stock yang bisa dikirim!'
                ) % sn.name)
            
            # Cek apakah sudah pernah keluar
            shipped = self.env['brodher.sn.move'].search([
                ('serial_number_id', '=', sn.id),
                ('move_type', '=', 'out'),
                ('picking_id.state', '=', 'done')
            ], limit=1)
            
            if shipped:
                raise UserError(_(
                    '❌ SERIAL NUMBER SUDAH KELUAR GUDANG!\n\n'
                    '🔹 Serial Number: %s\n'
                    '🔹 Shipped in: %s\n'
                    '🔹 Date: %s\n'
                    '🔹 User: %s\n\n'
                    '⚠️ SN ini sudah tidak ada di gudang!'
                ) % (
                    sn.name,
                    shipped.picking_id.name,
                    shipped.move_date.strftime('%Y-%m-%d %H:%M:%S'),
                    shipped.user_id.name
                ))
            
            # Status harus available
            if sn.sn_status != 'available':
                raise UserError(_(
                    '❌ STATUS SERIAL NUMBER TIDAK VALID!\n\n'
                    '🔹 Serial Number: %s\n'
                    '🔹 Current Status: %s\n'
                    '🔹 Required Status: AVAILABLE\n\n'
                    '⚠️ Hanya SN dengan status Available yang bisa dikirim!'
                ) % (sn.name, sn.sn_status.upper()))
        
        # Validation: Product in picking
        product_in_picking = sn.product_id in self.picking_id.move_ids_without_package.mapped('product_id')
        if not product_in_picking:
            raise UserError(_(
                '❌ PRODUCT TIDAK ADA DI PICKING INI!\n\n'
                '🔹 Serial Number: %s\n'
                '🔹 Product: %s\n\n'
                '⚠️ Product ini tidak ada dalam picking.'
            ) % (sn.name, sn.product_id.name))
        
        # Validation: Already scanned in THIS picking
        existing_in_this_picking = self.env['brodher.sn.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('serial_number_id', '=', sn.id)
        ])
        if existing_in_this_picking:
            raise UserError(_(
                '❌ SUDAH DI-SCAN DI PICKING INI!\n\n'
                '🔹 Serial Number: %s\n'
                '🔹 Scanned by: %s\n'
                '🔹 Date: %s'
            ) % (sn.name, existing_in_this_picking.user_id.name, existing_in_this_picking.move_date))
        
        # ========================================
        # ALL VALIDATIONS PASSED - CREATE RECORD
        # ========================================
        
        move_vals = {
            'serial_number_id': sn.id,
            'move_type': self.move_type,
            'location_src_id': self.location_src_id.id if self.location_src_id else False,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
        }
        
        sn_move = self.env['brodher.sn.move'].create(move_vals)
        
        # Update SN status
        update_vals = {'last_sn_move_date': fields.Datetime.now()}
        
        if self.move_type == 'in':
            update_vals['sn_status'] = 'available'
        elif self.move_type == 'out':
            update_vals['sn_status'] = 'used'
        elif self.move_type == 'internal':
            update_vals['sn_status'] = 'reserved'
        
        sn.write(update_vals)
        
        # Auto assign to move line
        move_line_found = False
        for move_line in self.picking_id.move_line_ids_without_package:
            if move_line.product_id == sn.product_id and not move_line.lot_id:
                move_line.write({
                    'lot_id': sn.id,
                    'lot_name': sn.name,
                    'quantity': 1,
                })
                _logger.info('✓ Auto assigned SN %s to move line' % sn.name)
                move_line_found = True
                break
        
        _logger.info('✓ SN %s scanned - Type: %s, Picking: %s' % (sn.name, self.move_type, self.picking_id.name))
         # If no empty move line, create new one
        if not move_line_found:
            # Find the stock move for this product
            stock_move = self.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id == sn.product_id
            )
            
            if stock_move:
                stock_move = stock_move[0]
                
                # Create new move line
                self.env['stock.move.line'].create({
                    'picking_id': self.picking_id.id,
                    'move_id': stock_move.id,
                    'product_id': sn.product_id.id,
                    'product_uom_id': sn.product_id.uom_id.id,
                    'location_id': self.location_src_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'lot_id': sn.id,
                    'lot_name': sn.name,
                    'quantity': 1,
                    'qty_done': 1,  # IMPORTANT: Set qty_done
                    'company_id': self.env.company.id,
                })
                _logger.info('✓ Created new move line for SN %s' % sn.name)
        # Return wizard for next scan
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_move_type': self.move_type,
                'default_location_src_id': self.location_src_id.id if self.location_src_id else False,
                'default_location_dest_id': self.location_dest_id.id,
                'default_input_method': self.input_method,
            }
        }

    def action_done(self):
        is_complete, error_msg = self.picking_id._check_sn_scan_completion()
        if not is_complete:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'brodher.sn.validation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_picking_id': self.picking_id.id,
                    'default_warning_message': error_msg,
                }
            }
        return {'type': 'ir.actions.act_window_close'}