# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ScanSNWizard(models.TransientModel):
    _name = 'brodher.scan.sn.wizard'
    _description = 'Scan Serial Number Wizard'
    
    # ... (field lainnya tetap sama) ...
# ... (field lainnya tetap sama) ...
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', required=True)
    picking_name = fields.Char(related='picking_id.name', string='Picking')
    picking_type = fields.Selection(related='picking_id.picking_type_code', string='Type')
    input_method = fields.Selection([('scan', 'Scan QR Code'), ('manual', 'Select Manually')], default='scan', required=True)
    scanned_sn = fields.Char(string='Scan Serial Number')
    serial_number_id = fields.Many2one('stock.lot', string='Select Serial Number', domain="[('id', 'in', available_sn_ids)]")
    available_sn_ids = fields.Many2many('stock.lot', compute='_compute_available_sn_ids', string='Available SNs')
    move_type = fields.Selection([('in', 'Stock In'), ('out', 'Stock Out'), ('internal', 'Internal Transfer')], required=True, default='in')
    location_src_id = fields.Many2one('stock.location', string='From')
    location_dest_id = fields.Many2one('stock.location', string='To', required=True)
    notes = fields.Text(string='Notes')
    sn_info = fields.Html(string='Serial Number Info', compute='_compute_sn_info')
    total_scanned = fields.Integer(string='Total Scanned', compute='_compute_total_scanned')
    scanned_list = fields.Html(string='Scanned List', compute='_compute_scanned_list')
    expected_quantities = fields.Html(string='Expected Quantities', compute='_compute_expected_quantities')

    # Tambahan field untuk notifikasi jika tidak ada SN
    has_sn_products = fields.Boolean(compute='_compute_has_sn_products')
    @api.depends('picking_id')
    def _compute_has_sn_products(self):
        for wizard in self:
            # Cek apakah ada produk dengan tracking serial
            sn_moves = wizard.picking_id.move_ids_without_package.filtered(lambda m: m.product_id.tracking == 'serial')
            wizard.has_sn_products = bool(sn_moves)
    @api.depends('picking_id', 'move_type')
    def _compute_available_sn_ids(self):
        for wizard in self:
            if not wizard.picking_id:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # AMBIL produk yang memang di-set tracking 'serial'
            products = wizard.picking_id.move_ids_without_package.mapped('product_id').filtered(lambda p: p.tracking == 'serial')
            
            # Domain dasar: harus produk yang ada di picking dan punya sn_type (Man/Woman)
            domain = [('product_id', 'in', products.ids), ('sn_type', '!=', False)]
            
            # Jika Stock Out, hanya tampilkan yang statusnya Available atau Reserved
            if wizard.move_type == 'out':
                domain.append(('sn_status', 'in', ['available', 'reserved']))
            
            # Jangan tampilkan SN yang sudah di-scan di picking ini
            already_scanned = wizard.picking_id.sn_move_ids.mapped('serial_number_id').ids
            if already_scanned:
                domain.append(('id', 'not in', already_scanned))
            
            available_sns = self.env['stock.lot'].search(domain)
            wizard.available_sn_ids = [(6, 0, available_sns.ids)]

    @api.depends('picking_id')
    def _compute_expected_quantities(self):
        for wizard in self:
            if wizard.picking_id:
                html = '<div style="margin: 10px 0;"><strong>Products to Scan:</strong>'
                html += '<table class="table table-sm table-bordered" style="margin-top: 5px;">'
                html += '<thead><tr><th>Product</th><th>Expected</th><th>Scanned</th><th>Remaining</th><th>Status</th></tr></thead><tbody>'
                
                # Filter hanya line yang produknya pakai Serial Number
                sn_moves = wizard.picking_id.move_ids_without_package.filtered(lambda m: m.product_id.tracking == 'serial')
                
                if not sn_moves:
                    wizard.expected_quantities = '<div class="alert alert-warning">No products with Serial Number tracking found in this picking.</div>'
                    continue

                for move in sn_moves:
                    expected = int(move.product_uom_qty)
                    # Hitung berdasarkan SN Move yang terhubung ke picking ini untuk produk tsb
                    scanned = len(wizard.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_id == move.product_id
                    ))
                    remaining = max(0, expected - scanned)
                    
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
                    html += f'<td>{move.product_id.display_name}</td>'
                    html += f'<td class="text-center">{expected}</td>'
                    html += f'<td class="text-center"><strong>{scanned}</strong></td>'
                    html += f'<td class="text-center"><strong style="color: red;">{remaining}</strong></td>'
                    html += f'<td class="text-center">{status}</td></tr>'
                
                html += '</tbody></table></div>'
                wizard.expected_quantities = html
            else:
                wizard.expected_quantities = ''
    @api.depends('picking_id', 'picking_id.sn_move_ids')
    def _compute_total_scanned(self):
            for wizard in self:
                # Menghitung jumlah SN yang sudah berhasil di-scan untuk picking ini
                wizard.total_scanned = len(wizard.picking_id.sn_move_ids) if wizard.picking_id else 0
    @api.depends('scanned_sn', 'serial_number_id', 'input_method')
    def _compute_sn_info(self):
        for wizard in self:
            sn = False
            if wizard.input_method == 'scan' and wizard.scanned_sn:
                # Cari SN berdasarkan nama dan pastikan itu produk SN kita
                sn = self.env['stock.lot'].search([('name', '=', wizard.scanned_sn)], limit=1)
            elif wizard.input_method == 'manual' and wizard.serial_number_id:
                sn = wizard.serial_number_id
            
            if sn:
                # Validasi apakah produk SN tersebut ada di daftar picking
                product_in_picking = sn.product_id in wizard.picking_id.move_ids_without_package.mapped('product_id')
                
                if not product_in_picking:
                    wizard.sn_info = f'''<div class="alert alert-warning">
                        <strong>⚠️ Product Mismatch:</strong> SN <b>{sn.name}</b> belongs to <b>{sn.product_id.name}</b> which is NOT in this picking.
                    </div>'''
                else:
                    status_color = {'available': '#d4edda', 'reserved': '#fff3cd', 'used': '#f8d7da'}.get(sn.sn_status, '#f0f0f0')
                    wizard.sn_info = f'''<div style="padding: 10px; background: {status_color}; border-radius: 5px; border: 1px solid #ccc;">
                        <table class="table table-sm" style="margin-bottom: 0;">
                            <tr><td><strong>SN:</strong></td><td><b>{sn.name}</b></td></tr>
                            <tr><td><strong>Product:</strong></td><td>{sn.product_id.name}</td></tr>
                            <tr><td><strong>Status:</strong></td><td>{sn.sn_status.upper() if sn.sn_status else 'NEW'}</td></tr>
                        </table>
                    </div>'''
            elif (wizard.input_method == 'scan' and wizard.scanned_sn):
                 wizard.sn_info = '<div class="alert alert-danger">❌ Serial Number not found in system!</div>'
            else:
                wizard.sn_info = '<div class="text-muted">Waiting for scan or selection...</div>'
    
    @api.onchange('input_method')
    def _onchange_input_method(self):
        if self.input_method == 'scan':
            self.serial_number_id = False
        else:
            self.scanned_sn = False
    
    def action_confirm_scan(self):
        self.ensure_one()
        
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan or enter serial number!'))
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn), ('sn_type', '!=', False)], limit=1)
            if not sn:
                raise ValidationError(_('Serial Number %s not found!') % self.scanned_sn)
        else:
            if not self.serial_number_id:
                raise UserError(_('Please select a serial number!'))
            sn = self.serial_number_id
        
        product_in_picking = sn.product_id in self.picking_id.move_ids_without_package.mapped('product_id')
        if not product_in_picking:
            raise UserError(_('Product "%s" is not in this picking!') % sn.product_id.name)
        
        existing = self.env['brodher.sn.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('serial_number_id', '=', sn.id)
        ])
        if existing:
            raise UserError(_('Serial Number %s already scanned!') % sn.name)
        
        if self.move_type == 'out' and sn.sn_status not in ['available', 'reserved']:
            raise UserError(_('Serial Number %s is not available! Status: %s') % (sn.name, sn.sn_status))
        
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': self.move_type,
            'location_src_id': self.location_src_id.id if self.location_src_id else False,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
        })
        
        update_vals = {'last_sn_move_date': fields.Datetime.now()}
        if self.move_type == 'in':
            update_vals['sn_status'] = 'available'
        elif self.move_type == 'out':
            update_vals['sn_status'] = 'used'
        sn.write(update_vals)
        
        for move_line in self.picking_id.move_line_ids_without_package:
            if move_line.product_id == sn.product_id and not move_line.lot_id:
                move_line.write({'lot_id': sn.id, 'lot_name': sn.name, 'quantity': 1})
                _logger.info('✓ Auto assigned SN to move line')
                break
        
        _logger.info('✓ SN %s scanned successfully' % sn.name)
        
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