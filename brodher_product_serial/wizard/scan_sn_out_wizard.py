# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ScanSNOutWizard(models.TransientModel):
    _name = 'brodher.scan.sn.out.wizard'
    _description = 'Scan Serial Number - OUTGOING'
    
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', required=True)
    picking_name = fields.Char(related='picking_id.name', string='Picking')
    
    input_method = fields.Selection([
        ('scan', 'Scan QR Code'),
        ('manual', 'Select Manually')
    ], string='Input Method', default='scan', required=True)
    
    scanned_sn = fields.Char(string='Scan Serial Number')
    serial_number_id = fields.Many2one('stock.lot', string='Select Serial Number',
                                       domain="[('id', 'in', available_sn_ids)]")
    available_sn_ids = fields.Many2many('stock.lot', compute='_compute_available_sn_ids')
    
    location_src_id = fields.Many2one('stock.location', string='From')
    location_dest_id = fields.Many2one('stock.location', string='To', required=True)
    notes = fields.Text(string='Notes')
    
    sn_info = fields.Html(string='Serial Number Info', compute='_compute_sn_info')
    total_scanned = fields.Integer(string='Total Scanned', compute='_compute_total_scanned')
    scanned_list = fields.Html(string='Scanned List', compute='_compute_scanned_list')
    expected_quantities = fields.Html(string='Expected Quantities', compute='_compute_expected_quantities')
    
    @api.depends('picking_id')
    def _compute_available_sn_ids(self):
        """
        Get available SNs for OUTGOING/INTERNAL
        Show SNs with status 'used' (in stock)
        """
        for wizard in self:
            if not wizard.picking_id:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # Get products
            products = wizard.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.tracking == 'serial' and
                        m.product_id.product_tmpl_id.sn_product_type
            ).mapped('product_id')
            
            if not products:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # Already scanned in this picking
            already_scanned = wizard.picking_id.sn_move_ids.mapped('serial_number_id.id')
            
            # Domain: ONLY 'used' status (for OUTGOING/INTERNAL)
            domain = [
                ('product_id', 'in', products.ids),
                ('sn_type', '!=', False),
                ('sn_status', '=', 'used'),  # ← For internal/delivery, use 'used'
            ]
            
            if already_scanned:
                domain.append(('id', 'not in', already_scanned))
            
            available_sns = self.env['stock.lot'].search(domain, order='name')
            
            _logger.info(f'[SCAN OUT] Found {len(available_sns)} SNs with status=used')

            wizard.available_sn_ids = [(6, 0, available_sns.ids)]

    @api.depends('picking_id')
    def _compute_total_scanned(self):
        for wizard in self:
            wizard.total_scanned = len(wizard.picking_id.sn_move_ids) if wizard.picking_id else 0
    
    @api.depends('picking_id')
    def _compute_expected_quantities(self):
        for wizard in self:
            if wizard.picking_id:
                html = '<div class="alert alert-warning"><strong>📤 OUTGOING - Barang Keluar</strong></div>'
                html += '<table class="table table-sm table-bordered">'
                html += '<thead><tr><th>Product</th><th>Expected</th><th>Scanned</th><th>Remaining</th></tr></thead><tbody>'
                
                for move in wizard.picking_id.move_ids_without_package:
                    if move.product_id.tracking != 'serial' or not move.product_id.product_tmpl_id.sn_product_type:
                        continue
                    
                    expected = int(move.product_uom_qty)
                    scanned = len(wizard.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_id == move.product_id
                    ))
                    remaining = expected - scanned
                    
                    status_color = '#d4edda' if scanned >= expected else ('#fff3cd' if scanned > 0 else '')
                    html += f'<tr style="background: {status_color};">'
                    html += f'<td>{move.product_id.name}</td>'
                    html += f'<td class="text-center">{expected}</td>'
                    html += f'<td class="text-center"><strong>{scanned}</strong></td>'
                    html += f'<td class="text-center"><strong style="color: red;">{remaining}</strong></td></tr>'
                
                html += '</tbody></table>'
                wizard.expected_quantities = html
            else:
                wizard.expected_quantities = ''
    
    @api.depends('picking_id')
    def _compute_scanned_list(self):
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sn_move_ids:
                html = '<strong>Recently Scanned:</strong><table class="table table-sm">'
                html += '<thead><tr><th>SN</th><th>Product</th><th>Time</th></tr></thead><tbody>'
                for move in wizard.picking_id.sn_move_ids.sorted(lambda m: m.move_date, reverse=True)[:5]:
                    html += f'<tr><td><code>{move.serial_number_name}</code></td>'
                    html += f'<td>{move.product_tmpl_id.name}</td>'
                    html += f'<td>{move.move_date.strftime("%H:%M:%S")}</td></tr>'
                html += '</tbody></table>'
                wizard.scanned_list = html
            else:
                wizard.scanned_list = '<p class="text-muted">No SN scanned yet</p>'
    
    @api.depends('scanned_sn', 'serial_number_id', 'input_method')
    def _compute_sn_info(self):
        for wizard in self:
            sn = None
            if wizard.input_method == 'scan' and wizard.scanned_sn:
                sn = self.env['stock.lot'].search([('name', '=', wizard.scanned_sn.strip())], limit=1)
            elif wizard.input_method == 'manual' and wizard.serial_number_id:
                sn = wizard.serial_number_id
            
            if sn:
                # Check if already scanned
                already_scanned = wizard.picking_id.sn_move_ids.filtered(
                    lambda sm: sm.serial_number_id == sn
                )
                
                if already_scanned:
                    wizard.sn_info = f'''<div class="alert alert-warning">
                        <h5>⚠️ Already Scanned!</h5>
                        <p>SN: <strong>{sn.name}</strong><br/>
                        Scanned at: {already_scanned[0].move_date.strftime("%Y-%m-%d %H:%M:%S")}</p></div>'''
                
                elif sn.sn_status == 'available':
                    wizard.sn_info = f'''<div class="alert alert-danger">
                        <h5>❌ Not In Stock!</h5>
                        <p>SN: <strong>{sn.name}</strong><br/>
                        Status: <strong>AVAILABLE</strong><br/>
                        This SN has not been received yet.</p></div>'''
                
                elif sn.sn_status == 'reserved':
                    wizard.sn_info = f'''<div class="alert alert-danger">
                        <h5>❌ Already Shipped!</h5>
                        <p>SN: <strong>{sn.name}</strong><br/>
                        Status: <strong>RESERVED</strong><br/>
                        This SN has already left the warehouse.</p></div>'''
                
                elif sn.sn_status == 'used':
                    # Check if already shipped
                    shipped = self.env['brodher.sn.move'].search([
                        ('serial_number_id', '=', sn.id),
                        ('move_type', '=', 'out'),
                        ('picking_id.state', '=', 'done')
                    ], limit=1)
                    
                    if shipped:
                        wizard.sn_info = f'''<div class="alert alert-danger">
                            <h5>❌ Already Shipped!</h5>
                            <p>SN: <strong>{sn.name}</strong><br/>
                            Shipped in: {shipped.picking_id.name}<br/>
                            Date: {shipped.move_date.strftime("%Y-%m-%d %H:%M")}</p></div>'''
                    else:
                        wizard.sn_info = f'''<div class="alert alert-success">
                            <h5>✓ Ready to Ship</h5>
                            <p>SN: <strong>{sn.name}</strong><br/>
                            Product: {sn.product_id.name}<br/>
                            Type: {'Man' if sn.sn_type == 'M' else 'Woman'}<br/>
                            Status: <span class="badge badge-success">IN STOCK</span></p></div>'''
                else:
                    wizard.sn_info = f'''<div class="alert alert-warning">
                        <h5>⚠️ Unknown Status</h5>
                        <p>SN: <strong>{sn.name}</strong><br/>
                        Status: <strong>{sn.sn_status.upper()}</strong></p></div>'''
            
            elif wizard.input_method == 'scan' and wizard.scanned_sn:
                wizard.sn_info = f'<div class="alert alert-warning">SN <strong>{wizard.scanned_sn}</strong> not found!</div>'
            else:
                wizard.sn_info = '<div class="alert alert-info">📱 Ready to scan...</div>'
    
    @api.onchange('input_method')
    def _onchange_input_method(self):
        if self.input_method == 'scan':
            self.serial_number_id = False
        else:
            self.scanned_sn = False
    
    def action_confirm_scan1(self):
        """Confirm scan - OUTGOING (simplified)"""
        self.ensure_one()
        
        # Get SN
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn.strip())], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select serial number!'))
            sn = self.serial_number_id
        
        # Validate: Already scanned?
        already_scanned = self.picking_id.sn_move_ids.filtered(
            lambda sm: sm.serial_number_id == sn
        )
        
        if already_scanned:
            raise UserError(_(
                '⚠️ SN %s already scanned!\n\nScanned at: %s'
            ) % (sn.name, already_scanned[0].move_date.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Validate: Status must be 'used'
        if sn.sn_status != 'used':
            raise UserError(_(
                '❌ SN %s cannot be shipped!\n\n'
                'Status: %s\n\n'
                'Only SNs with status "USED" (in stock) can be shipped.'
            ) % (sn.name, sn.sn_status.upper()))
        
        # Validate: Must be received but not shipped
        received = self.env['brodher.sn.move'].search([
            ('serial_number_id', '=', sn.id),
            ('move_type', '=', 'in'),
            ('picking_id.state', '=', 'done')
        ], limit=1)
        
        if not received:
            raise UserError(_('❌ SN %s not in stock!') % sn.name)
        
        shipped = self.env['brodher.sn.move'].search([
            ('serial_number_id', '=', sn.id),
            ('move_type', '=', 'out'),
            ('picking_id.state', '=', 'done')
        ], limit=1)
        
        if shipped:
            raise UserError(_(
                '❌ SN %s already shipped!\n\nShipped in: %s'
            ) % (sn.name, shipped.picking_id.name))
        
        # Validate: Product match
        picking_products = self.picking_id.move_ids_without_package.mapped('product_id')
        if sn.product_id not in picking_products:
            raise UserError(_(
                '❌ Product mismatch!\n\nSN: %s\nProduct: %s'
            ) % (sn.name, sn.product_id.display_name))
        
        # ==========================================
        # 1. Create brodher.sn.move (tracking)
        # ==========================================
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': 'out',
            'location_src_id': self.location_src_id.id if self.location_src_id else False,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
            'user_id': self.env.user.id,
            'move_date': fields.Datetime.now(),
        })
        
        _logger.info(f'[SCAN OUT] ✓ Created sn_move for {sn.name}')
        
        # ==========================================
        # 2. Create stock.move.line
        # ==========================================
        
        # Find stock.move
        stock_move = self.picking_id.move_ids_without_package.filtered(
            lambda m: m.product_id == sn.product_id
        )[:1]
        
        if not stock_move:
            raise UserError(_('Stock move not found for %s') % sn.product_id.display_name)
        
        # Create move_line
        loc_src = self.location_src_id if self.location_src_id else stock_move.location_id
        loc_dest = self.location_dest_id
        
        self.env['stock.move.line'].create({
            'picking_id': self.picking_id.id,
            'move_id': stock_move.id,
            'product_id': sn.product_id.id,
            'product_uom_id': sn.product_id.uom_id.id,
            'location_id': loc_src.id,
            'location_dest_id': loc_dest.id,
            'lot_id': sn.id,
            'lot_name': sn.name,
            'quantity': 1.0,
            'company_id': self.env.company.id,
        })
        
        _logger.info(f'[SCAN OUT] ✓ Created move_line for {sn.name}')
        
        # ==========================================
        # 3. Update SN status ONLY if external (not internal)
        # ==========================================
        
        # Check if destination is external (customer)
        if loc_dest.usage == 'customer':
            # External delivery → change to 'reserved' (shipped out)
            sn.write({
                'sn_status': 'reserved',
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] ✓ SN {sn.name} status → RESERVED (external delivery)')
        
        elif loc_dest.usage == 'internal':
            # Internal transfer → status stays 'used' (still in warehouse)
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] ✓ SN {sn.name} status → USED (internal transfer, no status change)')
        
        else:
            # Other location types (e.g., supplier return)
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] ✓ SN {sn.name} last_sn_move_date updated (location: {loc_dest.usage})')
        
        
        # Clear input
        self.scanned_sn = ''
        self.serial_number_id = False
        
        # Return to wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.out.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_location_src_id': self.location_src_id.id if self.location_src_id else False,
                'default_location_dest_id': self.location_dest_id.id,
                'default_input_method': self.input_method,
            }
        }
    def action_confirm_scan2(self):
        """Confirm scan - OUTGOING (simplified)"""
        self.ensure_one()
        
        # Get SN
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn.strip())], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select serial number!'))
            sn = self.serial_number_id
        
        # ✨ VALIDASI 1: Cek apakah SN sudah di-scan di picking ini
        already_scanned = self.picking_id.sn_move_ids.filtered(
            lambda sm: sm.serial_number_id == sn
        )
        
        if already_scanned:
            raise UserError(_(
                '⚠️ SN %s SUDAH DI-SCAN!\n\n'
                'Serial number ini sudah di-input pada picking ini.\n'
                'Scanned at: %s\n\n'
                'Silakan scan SN yang lain.'
            ) % (sn.name, already_scanned[0].move_date.strftime("%Y-%m-%d %H:%M:%S")))
        
        # Validate: Status must be 'used'
        if sn.sn_status != 'used':
            raise UserError(_(
                '❌ SN %s cannot be shipped!\n\n'
                'Status: %s\n\n'
                'Only SNs with status "USED" (in stock) can be shipped.'
            ) % (sn.name, sn.sn_status.upper()))
        
        # Validate: Must be received but not shipped
        received = self.env['brodher.sn.move'].search([
            ('serial_number_id', '=', sn.id),
            ('move_type', '=', 'in'),
            ('picking_id.state', '=', 'done')
        ], limit=1)
        
        if not received:
            raise UserError(_('❌ SN %s not in stock!') % sn.name)
        
        shipped = self.env['brodher.sn.move'].search([
            ('serial_number_id', '=', sn.id),
            ('move_type', '=', 'out'),
            ('picking_id.state', '=', 'done')
        ], limit=1)
        
        if shipped:
            raise UserError(_(
                '❌ SN %s already shipped!\n\nShipped in: %s'
            ) % (sn.name, shipped.picking_id.name))
        
        # Validate: Product match
        picking_products = self.picking_id.move_ids_without_package.mapped('product_id')
        if sn.product_id not in picking_products:
            raise UserError(_(
                '❌ Product mismatch!\n\nSN: %s\nProduct: %s'
            ) % (sn.name, sn.product_id.display_name))
        
        # ✨ VALIDASI 2: Cek apakah sudah mencapai expected quantity
        stock_move = self.picking_id.move_ids_without_package.filtered(
            lambda m: m.product_id == sn.product_id
        )[:1]
        
        if stock_move:
            expected_qty = int(stock_move.product_uom_qty)
            scanned_qty = len(self.picking_id.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id == sn.product_id
            ))
            
            if scanned_qty >= expected_qty:
                raise UserError(_(
                    '⚠️ PRODUCT %s SUDAH LENGKAP!\n\n'
                    'Expected: %d\n'
                    'Sudah di-scan: %d\n\n'
                    'Tidak bisa menambah SN lagi untuk product ini.'
                ) % (sn.product_id.name, expected_qty, scanned_qty))
        
        # ==========================================
        # 1. Create brodher.sn.move (tracking)
        # ==========================================
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': 'out',
            'location_src_id': self.location_src_id.id if self.location_src_id else False,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
            'user_id': self.env.user.id,
            'move_date': fields.Datetime.now(),
        })
        
        _logger.info(f'[SCAN OUT] ✓ Created sn_move for {sn.name}')
        
        # ==========================================
        # 2. Create stock.move.line
        # ==========================================
        
        if not stock_move:
            raise UserError(_('Stock move not found for %s') % sn.product_id.display_name)
        
        # Create move_line
        loc_src = self.location_src_id if self.location_src_id else stock_move.location_id
        loc_dest = self.location_dest_id
        
        self.env['stock.move.line'].create({
            'picking_id': self.picking_id.id,
            'move_id': stock_move.id,
            'product_id': sn.product_id.id,
            'product_uom_id': sn.product_id.uom_id.id,
            'location_id': loc_src.id,
            'location_dest_id': loc_dest.id,
            'lot_id': sn.id,
            'lot_name': sn.name,
            'quantity': 1.0,
            'company_id': self.env.company.id,
        })
        
        _logger.info(f'[SCAN OUT] ✓ Created move_line for {sn.name}')
        
        # ==========================================
        # 3. Update SN status ONLY if external (not internal)
        # ==========================================
        
        # Check if destination is external (customer)
        if loc_dest.usage == 'customer':
            # External delivery → change to 'reserved' (shipped out)
            sn.write({
                'sn_status': 'reserved',
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] ✓ SN {sn.name} status → RESERVED (external delivery)')
        
        elif loc_dest.usage == 'internal':
            # Internal transfer → status stays 'used' (still in warehouse)
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] ✓ SN {sn.name} status → USED (internal transfer, no status change)')
        
        else:
            # Other location types (e.g., supplier return)
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] ✓ SN {sn.name} last_sn_move_date updated (location: {loc_dest.usage})')
        
        
        # Clear input
        self.scanned_sn = ''
        self.serial_number_id = False
        
        # Return to wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.out.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_location_src_id': self.location_src_id.id if self.location_src_id else False,
                'default_location_dest_id': self.location_dest_id.id,
                'default_input_method': self.input_method,
            }
        }
    def action_confirm_scan3(self):
        """Confirm scan - OUTGOING/INTERNAL (with stock check)"""
        self.ensure_one()
        
        # Get SN
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn.strip())], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select serial number!'))
            sn = self.serial_number_id
        
        # Validate: Already scanned?
        already_scanned = self.picking_id.sn_move_ids.filtered(lambda sm: sm.serial_number_id == sn)
        if already_scanned:
            raise UserError(_('⚠️ SN %s already scanned!') % sn.name)
        
        # Validate: Status must be 'used'
        if sn.sn_status != 'used':
            raise UserError(_(
                '❌ SN %s cannot be used!\n\nStatus: %s\n\n'
                'Only SNs with status "USED" (in stock) can be moved.'
            ) % (sn.name, sn.sn_status.upper()))
        
        # Validate: Product match
        picking_products = self.picking_id.move_ids_without_package.mapped('product_id')
        if sn.product_id not in picking_products:
            raise UserError(_('❌ Product mismatch!') % sn.product_id.display_name)
        
        # ==========================================
        # CRITICAL: Check actual stock availability
        # ==========================================
        source_location = self.location_src_id if self.location_src_id else self.picking_id.location_id
        
        quants = self.env['stock.quant'].search([
            ('lot_id', '=', sn.id),
            ('location_id', '=', source_location.id),
            ('quantity', '>', 0)
        ])
        
        if not quants:
            actual_quants = self.env['stock.quant'].search([
                ('lot_id', '=', sn.id),
                ('quantity', '>', 0)
            ])
            
            if actual_quants:
                actual_location = actual_quants[0].location_id.complete_name
                raise UserError(_(
                    '❌ SN %s not in source location!\n\n'
                    'Required location: %s\n'
                    'Actual location: %s\n\n'
                    'Please move the item first or scan from correct location.'
                ) % (sn.name, source_location.complete_name, actual_location))
            else:
                raise UserError(_(
                    '❌ SN %s has no stock!\n\n'
                    'This serial number is not available in any location.\n'
                    'Status: %s'
                ) % (sn.name, sn.sn_status.upper()))
        
        _logger.info(f'[SCAN OUT] ✓ Stock check passed: {sn.name} available at {source_location.complete_name}')
        
        # ==========================================
        # Create tracking record
        # ==========================================
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': 'out',
            'location_src_id': source_location.id,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
            'user_id': self.env.user.id,
            'move_date': fields.Datetime.now(),
        })
        
        # ==========================================
        # Create move_line
        # ==========================================
        stock_move = self.picking_id.move_ids_without_package.filtered(
            lambda m: m.product_id == sn.product_id
        )[:1]
        
        if not stock_move:
            raise UserError(_('Stock move not found'))
        
        self.env['stock.move.line'].create({
            'picking_id': self.picking_id.id,
            'move_id': stock_move.id,
            'product_id': sn.product_id.id,
            'product_uom_id': sn.product_id.uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': self.location_dest_id.id,
            'lot_id': sn.id,
            'lot_name': sn.name,
            'quantity': 1.0,
            'company_id': self.env.company.id,
        })
        
        # ==========================================
        # CRITICAL FIX: Update status based on destination
        # ==========================================
        dest_location = self.location_dest_id
        
        # Check if destination is EXTERNAL (customer/supplier)
        if dest_location.usage in ['customer', 'supplier', 'transit']:
            # EXTERNAL delivery → change to 'reserved' (shipped out)
            sn.write({
                'sn_status': 'reserved',
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → RESERVED (external delivery to {dest_location.usage})')
        
        elif dest_location.usage == 'internal':
            # INTERNAL transfer → status stays 'used' (still in warehouse)
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → USED (internal transfer, no status change)')
        
        else:
            # Other location types
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → last_sn_move_date updated (location: {dest_location.usage})')
        
        # Clear and return
        self.scanned_sn = ''
        self.serial_number_id = False
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.out.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_location_src_id': source_location.id,
                'default_location_dest_id': self.location_dest_id.id,
                'default_input_method': self.input_method,
            }
        }
    def action_confirm_scan4(self):
        """Confirm scan - OUTGOING/INTERNAL (with stock check)"""
        self.ensure_one()
        
        import logging
        _logger = logging.getLogger(__name__)
        
        # Get SN
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn.strip())], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select serial number!'))
            sn = self.serial_number_id
        
        # Validate: Already scanned in THIS picking?
        already_scanned = self.picking_id.sn_move_ids.filtered(lambda sm: sm.serial_number_id == sn)
        if already_scanned:
            raise UserError(_('⚠️ SN %s already scanned in this transfer!') % sn.name)
        
        # Validate: Status must be 'used'
        if sn.sn_status != 'used':
            raise UserError(_(
                '❌ SN %s cannot be used!\n\n'
                'Status: %s\n\n'
                'Only SNs with status "USED" (in stock) can be moved.'
            ) % (sn.name, sn.sn_status.upper()))
        
        # Validate: Product match
        picking_products = self.picking_id.move_ids_without_package.mapped('product_id')
        if sn.product_id not in picking_products:
            raise UserError(_('❌ Product mismatch!') % sn.product_id.display_name)
        
        # ==========================================
        # Get source and destination locations
        # ==========================================
        source_location = self.location_src_id if self.location_src_id else self.picking_id.location_id
        dest_location = self.location_dest_id
        
        _logger.info(f'[SCAN OUT] Transfer type: {self.picking_id.picking_type_code}')
        _logger.info(f'[SCAN OUT] From: {source_location.complete_name} (usage: {source_location.usage})')
        _logger.info(f'[SCAN OUT] To: {dest_location.complete_name} (usage: {dest_location.usage})')
        
        # ==========================================
        # Check stock availability in source location
        # ==========================================
        quants = self.env['stock.quant'].search([
            ('lot_id', '=', sn.id),
            ('location_id', '=', source_location.id),
            ('quantity', '>', 0)
        ])
        
        if not quants:
            # Find where it actually is
            actual_quants = self.env['stock.quant'].search([
                ('lot_id', '=', sn.id),
                ('quantity', '>', 0)
            ])
            
            if actual_quants:
                actual_location = actual_quants[0].location_id.complete_name
                raise UserError(_(
                    '❌ SN %s not in source location!\n\n'
                    'Required location: %s\n'
                    'Actual location: %s\n\n'
                    'Please scan from the correct source location.'
                ) % (sn.name, source_location.complete_name, actual_location))
            else:
                raise UserError(_(
                    '❌ SN %s has no stock!\n\n'
                    'This serial number is not available in any location.'
                ) % sn.name)
        
        _logger.info(f'[SCAN OUT] ✓ Stock check passed: {sn.name} available at {source_location.complete_name}')
        
        # ==========================================
        # REMOVED: "Already Shipped" check
        # For internal transfers, SN can be moved multiple times
        # Only check if destination is EXTERNAL
        # ==========================================
        
        if dest_location.usage in ['customer', 'supplier']:
            # For external delivery, check if already shipped
            shipped = self.env['brodher.sn.move'].search([
                ('serial_number_id', '=', sn.id),
                ('move_type', '=', 'out'),
                ('picking_id.state', '=', 'done'),
                ('picking_id.picking_type_code', '=', 'outgoing'),  # Only check actual deliveries
            ], limit=1)
            
            if shipped:
                raise UserError(_(
                    '❌ Already Shipped!\n\n'
                    'SN: %s\n'
                    'Shipped in: %s\n'
                    'Date: %s'
                ) % (sn.name, shipped.picking_id.name, shipped.move_date.strftime('%Y-%m-%d %H:%M')))
        
        # ==========================================
        # Create tracking record
        # ==========================================
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': 'out',
            'location_src_id': source_location.id,
            'location_dest_id': dest_location.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
            'user_id': self.env.user.id,
            'move_date': fields.Datetime.now(),
        })
        
        _logger.info(f'[SCAN OUT] ✓ Created sn_move for {sn.name}')
        
        # ==========================================
        # Create move_line
        # ==========================================
        stock_move = self.picking_id.move_ids_without_package.filtered(
            lambda m: m.product_id == sn.product_id
        )[:1]
        
        if not stock_move:
            raise UserError(_('Stock move not found'))
        
        self.env['stock.move.line'].create({
            'picking_id': self.picking_id.id,
            'move_id': stock_move.id,
            'product_id': sn.product_id.id,
            'product_uom_id': sn.product_id.uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'lot_id': sn.id,
            'lot_name': sn.name,
            'quantity': 1.0,
            'company_id': self.env.company.id,
        })
        
        _logger.info(f'[SCAN OUT] ✓ Created move_line for {sn.name}')
        
        # ==========================================
        # Update status based on destination type
        # ==========================================
        
        if dest_location.usage in ['customer', 'supplier', 'transit']:
            # EXTERNAL delivery → change to 'reserved' (shipped out of warehouse)
            sn.write({
                'sn_status': 'reserved',
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → RESERVED (external delivery)')
        
        elif dest_location.usage == 'internal':
            # INTERNAL transfer → status stays 'used' (still in warehouse)
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → USED (internal transfer, no status change)')
        
        else:
            # Other types (production, inventory, etc.)
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → last_sn_move_date updated')
        
        # Clear input
        self.scanned_sn = ''
        self.serial_number_id = False
        
        # Return to wizard
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.out.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_location_src_id': source_location.id,
                'default_location_dest_id': dest_location.id,
                'default_input_method': self.input_method,
            }
        }
    def action_confirm_scan(self):
        """Confirm scan - OUTGOING/INTERNAL (with stock check)"""
        self.ensure_one()
        
        import logging
        _logger = logging.getLogger(__name__)
        
        # Get SN
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn.strip())], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select serial number!'))
            sn = self.serial_number_id
        
        # Validate: Already scanned in THIS picking?
        already_scanned = self.picking_id.sn_move_ids.filtered(lambda sm: sm.serial_number_id == sn)
        if already_scanned:
            raise UserError(_('⚠️ SN %s already scanned in this transfer!') % sn.name)
        
        # Validate: Status must be 'used'
        if sn.sn_status != 'used':
            raise UserError(_(
                '❌ SN %s cannot be used!\n\n'
                'Status: %s\n\n'
                'Only SNs with status "USED" (in stock) can be moved.'
            ) % (sn.name, sn.sn_status.upper()))
        
        # Validate: Product match
        picking_products = self.picking_id.move_ids_without_package.mapped('product_id')
        if sn.product_id not in picking_products:
            raise UserError(_('❌ Product mismatch!') % sn.product_id.display_name)
        
        # ==========================================
        # Get locations
        # ==========================================
        source_location = self.location_src_id if self.location_src_id else self.picking_id.location_id
        dest_location = self.location_dest_id
        
        _logger.info(f'[SCAN OUT] {self.picking_id.picking_type_code}: {source_location.complete_name} → {dest_location.complete_name}')
        
        # ==========================================
        # Validate: Check stock in source location
        # ==========================================
        quants = self.env['stock.quant'].search([
            ('lot_id', '=', sn.id),
            ('location_id', '=', source_location.id),
            ('quantity', '>', 0)
        ])
        
        if not quants:
            actual_quants = self.env['stock.quant'].search([
                ('lot_id', '=', sn.id),
                ('quantity', '>', 0)
            ])
            
            if actual_quants:
                actual_location = actual_quants[0].location_id.complete_name
                raise UserError(_(
                    '❌ SN %s not in source location!\n\n'
                    'Required: %s\n'
                    'Current: %s\n\n'
                    'Please scan from correct location.'
                ) % (sn.name, source_location.complete_name, actual_location))
            else:
                raise UserError(_(
                    '❌ SN %s has no stock!'
                ) % sn.name)
        
        # ==========================================
        # Validate: Check quantity limit
        # ==========================================
        stock_move = self.picking_id.move_ids_without_package.filtered(
            lambda m: m.product_id == sn.product_id
        )[:1]
        
        if stock_move:
            demand_qty = int(stock_move.product_uom_qty)
            scanned_qty = len(self.picking_id.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_id == sn.product_id
            ))
            
            if scanned_qty >= demand_qty:
                raise UserError(_(
                    '⚠️ Quantity Limit Reached!\n\n'
                    'Product: %s\n'
                    'Demand: %s\n'
                    'Already Scanned: %s\n\n'
                    'Cannot scan more than demand quantity.'
                ) % (sn.product_id.display_name, demand_qty, scanned_qty))
        
        # ==========================================
        # REMOVED: "Already Shipped" check
        # SN can be moved internally multiple times
        # Only external delivery changes status to 'reserved'
        # ==========================================
        
        # Create tracking record
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': 'out',
            'location_src_id': source_location.id,
            'location_dest_id': dest_location.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
            'user_id': self.env.user.id,
            'move_date': fields.Datetime.now(),
        })
        
        # Create move_line
        if not stock_move:
            raise UserError(_('Stock move not found'))
        
        self.env['stock.move.line'].create({
            'picking_id': self.picking_id.id,
            'move_id': stock_move.id,
            'product_id': sn.product_id.id,
            'product_uom_id': sn.product_id.uom_id.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'lot_id': sn.id,
            'lot_name': sn.name,
            'quantity': 1.0,
            'company_id': self.env.company.id,
        })
        
        # Update status based on destination
        if dest_location.usage in ['customer', 'supplier', 'transit']:
            # External delivery
            sn.write({
                'sn_status': 'reserved',
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → RESERVED')
        else:
            # Internal transfer - keep status 'used'
            sn.write({
                'last_sn_move_date': fields.Datetime.now()
            })
            _logger.info(f'[SCAN OUT] {sn.name} → USED (no change)')
        
        # Clear input
        self.scanned_sn = ''
        self.serial_number_id = False
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.out.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_location_src_id': source_location.id,
                'default_location_dest_id': dest_location.id,
                'default_input_method': self.input_method,
            }
        }
    def action_done(self):
        """Close wizard"""
        return {'type': 'ir.actions.act_window_close'}