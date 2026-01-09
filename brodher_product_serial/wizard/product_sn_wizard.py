# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ScanSNWizard(models.TransientModel):
    _name = 'brodher.scan.sn.wizard'
    _description = 'Scan Serial Number Wizard'
    
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
            
            # UPDATE: Hanya ambil produk yang tracking-nya 'serial'
            products = wizard.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.tracking == 'serial'
            ).mapped('product_id')
            
            domain = [('product_id', 'in', products.ids), ('sn_type', '!=', False)]
            if wizard.move_type == 'out':
                domain.append(('sn_status', 'in', ['available', 'reserved']))
            
            already_scanned = wizard.picking_id.sn_move_ids.mapped('serial_number_id.id')
            if already_scanned:
                domain.append(('id', 'not in', already_scanned))
            
            available_sns = self.env['stock.lot'].search(domain)
            wizard.available_sn_ids = [(6, 0, available_sns.ids)]

    @api.depends('picking_id')
    def _compute_expected_quantities(self):
        for wizard in self:
            if wizard.picking_id:
                # UPDATE: Filter hanya produk yang memiliki tracking serial
                sn_moves = wizard.picking_id.move_ids_without_package.filtered(lambda m: m.product_id.tracking == 'serial')
                
                if not sn_moves:
                    wizard.expected_quantities = '<div class="alert alert-warning">No products in this picking require Serial Number scanning.</div>'
                    continue

                html = '<div style="margin: 10px 0;"><strong>Products to Scan:</strong>'
                html += '<table class="table table-sm table-bordered" style="margin-top: 5px;">'
                html += '<thead><tr><th>Product</th><th>Expected</th><th>Scanned</th><th>Remaining</th><th>Status</th></tr></thead><tbody>'
                
                for move in sn_moves:
                    expected = int(move.product_uom_qty)
                    scanned = len(wizard.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_id == move.product_id
                    ))
                    remaining = max(0, expected - scanned)
                    
                    if scanned >= expected:
                        status, row_style = '<span style="color: green;">✓ Complete</span>', 'background: #d4edda;'
                    elif scanned > 0:
                        status, row_style = '<span style="color: orange;">◐ Partial</span>', 'background: #fff3cd;'
                    else:
                        status, row_style = '<span style="color: red;">○ Pending</span>', ''
                    
                    html += f'<tr style="{row_style}"><td>{move.product_id.display_name}</td>'
                    html += f'<td class="text-center">{expected}</td>'
                    html += f'<td class="text-center"><strong>{scanned}</strong></td>'
                    html += f'<td class="text-center"><strong style="color: red;">{remaining}</strong></td>'
                    html += f'<td class="text-center">{status}</td></tr>'
                
                html += '</tbody></table></div>'
                wizard.expected_quantities = html
            else:
                wizard.expected_quantities = ''

    # ... (action_confirm_scan dan action_done tetap sama namun akan otomatis mengikuti filter di atas) ...
    def action_confirm_scan(self):
        self.ensure_one()
        # Validasi tambahan: Jika produk yang di-scan ternyata bukan tipe 'serial'
        sn = None
        if self.input_method == 'scan':
            sn = self.env['stock.lot'].search([('name', '=', self.scanned_sn)], limit=1)
        else:
            sn = self.serial_number_id
            
        if sn and sn.product_id.tracking != 'serial':
            raise UserError(_("Product %s does not use Serial Numbers!") % sn.product_id.name)
            
        # Kembalikan ke fungsi asal Anda untuk create move
        return super(ScanSNWizard, self).action_confirm_scan()