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
    has_sn_products = fields.Boolean(compute='_compute_has_sn_products')

    @api.depends('picking_id')
    def _compute_has_sn_products(self):
        for wizard in self:
            sn_moves = wizard.picking_id.move_ids_without_package.filtered(lambda m: m.product_id.tracking == 'serial')
            wizard.has_sn_products = bool(sn_moves)

    @api.depends('picking_id', 'move_type')
    def _compute_available_sn_ids(self):
        for wizard in self:
            if not wizard.picking_id:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            products = wizard.picking_id.move_ids_without_package.mapped('product_id').filtered(lambda p: p.tracking == 'serial')
            domain = [('product_id', 'in', products.ids), ('sn_type', '!=', False)]
            if wizard.move_type == 'out':
                domain.append(('sn_status', 'in', ['available', 'reserved']))
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
                sn_moves = wizard.picking_id.move_ids_without_package.filtered(lambda m: m.product_id.tracking == 'serial')
                if not sn_moves:
                    wizard.expected_quantities = '<div class="alert alert-warning">No products with Serial Number tracking found.</div>'
                    continue
                for move in sn_moves:
                    expected = int(move.product_uom_qty)
                    scanned = len(wizard.picking_id.sn_move_ids.filtered(lambda sm: sm.serial_number_id.product_id == move.product_id))
                    remaining = max(0, expected - scanned)
                    status = '<span style="color: green;">✓ Complete</span>' if scanned >= expected else \
                             ('<span style="color: orange;">◐ Partial</span>' if scanned > 0 else '<span style="color: red;">○ Pending</span>')
                    row_style = 'background: #d4edda;' if scanned >= expected else ('background: #fff3cd;' if scanned > 0 else '')
                    html += f'<tr style="{row_style}"><td>{move.product_id.display_name}</td><td class="text-center">{expected}</td>'
                    html += f'<td class="text-center"><strong>{scanned}</strong></td><td class="text-center" style="color:red;">{remaining}</td>'
                    html += f'<td class="text-center">{status}</td></tr>'
                html += '</tbody></table></div>'
                wizard.expected_quantities = html
            else:
                wizard.expected_quantities = ''

    @api.depends('picking_id', 'picking_id.sn_move_ids')
    def _compute_scanned_list(self):
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sn_move_ids:
                html = '<div style="max-height: 150px; overflow-y: auto; margin-top: 10px;">'
                html += '<strong>Recently Scanned:</strong><table class="table table-sm">'
                html += '<thead><tr><th>SN</th><th>Product</th><th>Time</th></tr></thead><tbody>'
                recent_moves = wizard.picking_id.sn_move_ids.sorted(lambda m: m.create_date, reverse=True)[:10]
                for move in recent_moves:
                    formatted_time = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, move.create_date))[11:19]
                    html += f'<tr><td><code>{move.serial_number_id.name}</code></td><td><small>{move.serial_number_id.product_id.name}</small></td><td><small>{formatted_time}</small></td></tr>'
                html += '</tbody></table></div>'
                wizard.scanned_list = html
            else:
                wizard.scanned_list = '<p class="text-muted">No serial numbers scanned yet</p>'

    @api.depends('picking_id', 'picking_id.sn_move_ids')
    def _compute_total_scanned(self):
        for wizard in self:
            wizard.total_scanned = len(wizard.picking_id.sn_move_ids) if wizard.picking_id else 0

    @api.depends('scanned_sn', 'serial_number_id', 'input_method')
    def _compute_sn_info(self):
        for wizard in self:
            sn = False
            if wizard.input_method == 'scan' and wizard.scanned_sn:
                sn = self.env['stock.lot'].search([('name', '=', wizard.scanned_sn)], limit=1)
            elif wizard.input_method == 'manual' and wizard.serial_number_id:
                sn = wizard.serial_number_id
            
            if sn:
                product_in_picking = sn.product_id in wizard.picking_id.move_ids_without_package.mapped('product_id')
                if not product_in_picking:
                    wizard.sn_info = f'<div class="alert alert-warning">⚠️ SN <b>{sn.name}</b> (Product: {sn.product_id.name}) is NOT in this picking.</div>'
                else:
                    status_color = {'available': '#d4edda', 'reserved': '#fff3cd', 'used': '#f8d7da'}.get(sn.sn_status, '#f0f0f0')
                    wizard.sn_info = f'<div style="padding:10px; background:{status_color}; border-radius:5px; border:1px solid #ccc;">' \
                                     f'<b>SN:</b> {sn.name}<br/><b>Product:</b> {sn.product_id.name}<br/><b>Status:</b> {sn.sn_status.upper() if sn.sn_status else "NEW"}</div>'
            elif wizard.scanned_sn:
                wizard.sn_info = '<div class="alert alert-danger">❌ Serial Number not found!</div>'
            else:
                wizard.sn_info = '<div class="text-muted">Waiting for scan...</div>'

    @api.onchange('input_method')
    def _onchange_input_method(self):
        self.serial_number_id = False
        self.scanned_sn = False

    def action_confirm_scan(self):
        self.ensure_one()
        if not self.has_sn_products:
            raise UserError(_('No SN products to scan.'))

        sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn)], limit=1) if self.input_method == 'scan' else self.serial_number_id
        if not sn: raise UserError(_('Serial Number not found!'))
        
        if sn.product_id not in self.picking_id.move_ids_without_package.mapped('product_id'):
            raise UserError(_('Product not in picking!'))

        if self.env['brodher.sn.move'].search([('picking_id', '=', self.picking_id.id), ('serial_number_id', '=', sn.id)]):
            raise UserError(_('Already scanned!'))

        # Create Custom Move
        self.env['brodher.sn.move'].create({
            'serial_number_id': sn.id,
            'move_type': self.move_type,
            'location_src_id': self.location_src_id.id,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
        })
        
        # Update SN Status
        sn.write({'sn_status': 'available' if self.move_type == 'in' else 'used', 'last_sn_move_date': fields.Datetime.now()})

        # Sync ke Move Lines Odoo
        move_line = self.picking_id.move_line_ids_without_package.filtered(lambda l: l.product_id == sn.product_id and not l.lot_id)
        if move_line:
            move_line[0].write({'lot_id': sn.id, 'quantity': 1.0})
        else:
            # Create new line if no empty line found
            self.env['stock.move.line'].create({
                'picking_id': self.picking_id.id,
                'product_id': sn.product_id.id,
                'lot_id': sn.id,
                'quantity': 1.0,
                'location_id': self.location_src_id.id,
                'location_dest_id': self.location_dest_id.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_done(self):
        self.ensure_one()
        
        # 1. CLEANUP: Hapus semua baris Move Line yang track SN tapi Lot-nya Kosong
        # Ini untuk mencegah error "You need to supply a Lot/Serial Number"
        empty_sn_lines = self.picking_id.move_line_ids_without_package.filtered(
            lambda l: l.product_id.tracking == 'serial' and not l.lot_id
        )
        if empty_sn_lines:
            empty_sn_lines.unlink()

        # 2. VALIDASI KELENGKAPAN (Hanya jika ada produk SN)
        if self.has_sn_products:
            is_complete, error_msg = self.picking_id._check_sn_scan_completion()
            if not is_complete:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'brodher.sn.validation.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_picking_id': self.picking_id.id, 'default_warning_message': error_msg}
                }

        # 3. FINAL VALIDATE
        try:
            self.picking_id.button_validate()
        except Exception as e:
            _logger.error("Validation failed: %s" % str(e))
        
        return {'type': 'ir.actions.act_window_close'}