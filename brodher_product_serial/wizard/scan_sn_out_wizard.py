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
        """Get available SNs for OUTGOING - yang ADA DI STOCK"""
        for wizard in self:
            if not wizard.picking_id:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            products = wizard.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.tracking == 'serial' and m.product_id.product_tmpl_id.sn_product_type
            ).mapped('product_id')
            
            if not products:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # OUTGOING: Hanya SN yang SUDAH masuk tapi BELUM keluar
            received_sns = self.env['brodher.sn.move'].search([
                ('move_type', '=', 'in'),
                ('picking_id.state', '=', 'done')
            ]).mapped('serial_number_id.id')
            
            shipped_sns = self.env['brodher.sn.move'].search([
                ('move_type', '=', 'out'),
                ('picking_id.state', '=', 'done')
            ]).mapped('serial_number_id.id')
            
            available_in_stock = list(set(received_sns) - set(shipped_sns))
            
            already_scanned_this = wizard.picking_id.sn_move_ids.mapped('serial_number_id.id')
            
            domain = [
                ('product_id', 'in', products.ids),
                ('sn_type', '!=', False),
                ('sn_status', '=', 'available'),
            ]
            
            if available_in_stock:
                domain.append(('id', 'in', available_in_stock))
            else:
                domain.append(('id', '=', False))  # No stock
            
            if already_scanned_this:
                domain.append(('id', 'not in', already_scanned_this))
            
            available_sns = self.env['stock.lot'].search(domain, order='name')
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
                sn = self.env['stock.lot'].search([('name', '=', wizard.scanned_sn), ('sn_type', '!=', False)], limit=1)
            elif wizard.input_method == 'manual' and wizard.serial_number_id:
                sn = wizard.serial_number_id
            
            if sn:
                # Check stock status
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
                
                if not received:
                    wizard.sn_info = f'''<div class="alert alert-danger">
                        <h5>❌ BELUM MASUK GUDANG!</h5>
                        <p>SN: <strong>{sn.name}</strong><br/>
                        This SN has never been received. Cannot ship!</p></div>'''
                elif shipped:
                    wizard.sn_info = f'''<div class="alert alert-danger">
                        <h5>❌ ALREADY SHIPPED!</h5>
                        <p>SN: <strong>{sn.name}</strong><br/>
                        Shipped in: {shipped.picking_id.name}<br/>
                        Date: {shipped.move_date.strftime("%Y-%m-%d %H:%M")}</p></div>'''
                else:
                    wizard.sn_info = f'''<div class="alert alert-success">
                        <h5>✓ IN STOCK - Ready to Ship</h5>
                        <p>SN: <strong>{sn.name}</strong><br/>
                        Product: {sn.product_id.name}<br/>
                        Type: {'Man' if sn.sn_type == 'M' else 'Woman'}<br/>
                        Received: {received.move_date.strftime("%Y-%m-%d")}</p></div>'''
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
    
    def action_confirm_scan(self):
        """Confirm scan - OUTGOING"""
        self.ensure_one()
        
        # Get SN
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn), ('sn_type', '!=', False)], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select serial number!'))
            sn = self.serial_number_id
        
        # Validate: Must be in stock
        received = self.env['brodher.sn.move'].search([
            ('serial_number_id', '=', sn.id),
            ('move_type', '=', 'in'),
            ('picking_id.state', '=', 'done')
        ], limit=1)
        
        if not received:
            raise UserError(_('❌ SN %s BELUM MASUK GUDANG!\n\nCannot ship!') % sn.name)
        
        shipped = self.env['brodher.sn.move'].search([
            ('serial_number_id', '=', sn.id),
            ('move_type', '=', 'out'),
            ('picking_id.state', '=', 'done')
        ], limit=1)
        
        if shipped:
            raise UserError(_(
                '❌ SN %s SUDAH KELUAR!\n\nShipped in: %s\nDate: %s'
            ) % (sn.name, shipped.picking_id.name, shipped.move_date))
        
        # Create SN move
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': 'out',
            'location_src_id': self.location_src_id.id if self.location_src_id else False,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
        })
        
        # Update SN
        sn.write({'sn_status': 'used', 'last_sn_move_date': fields.Datetime.now()})
        
        # Create move line with CORRECT locations
        stock_move = self.picking_id.move_ids_without_package.filtered(lambda m: m.product_id == sn.product_id)
        if stock_move:
            stock_move = stock_move[0]
            
            # CRITICAL: Locations for outgoing
            loc_src = self.location_src_id  # Stock location
            loc_dest = self.location_dest_id  # Customer location
            
            _logger.info('OUTGOING Move Line: %s → %s' % (loc_src.complete_name, loc_dest.complete_name))
            
            self.env['stock.move.line'].create({
                'picking_id': self.picking_id.id,
                'move_id': stock_move.id,
                'product_id': sn.product_id.id,
                'product_uom_id': sn.product_id.uom_id.id,
                'location_id': loc_src.id,
                'location_dest_id': loc_dest.id,
                'lot_id': sn.id,
                'lot_name': sn.name,
                'quantity': 1,
                'qty_done': 1,
                'company_id': self.env.company.id,
            })
            
            # Force recompute
            stock_move._action_assign()
            stock_move._recompute_state()
        
        _logger.info('✓ OUTGOING: SN %s scanned' % sn.name)
        
        # Return for next scan
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
    
    def action_done(self):
        return {'type': 'ir.actions.act_window_close'}  