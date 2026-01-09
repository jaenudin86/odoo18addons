# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import qrcode
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)

class StockLot(models.Model):
    _inherit = 'stock.lot'
    
    sn_type = fields.Selection([
        ('M', 'Man'), ('W', 'Woman')
    ], string='SN Type', index=True)
    
    year_code = fields.Char(string='Year Code', size=2, readonly=True, index=True)
    sequence_number = fields.Integer(string='Sequence Number', readonly=True, index=True)
    
    sn_status = fields.Selection([
        ('available', 'Available'),
        ('used', 'Used'),
        ('reserved', 'Reserved')
    ], string='Status', default='available', index=True)
    
    qc_passed = fields.Boolean(string='QC Passed', default=True)
    sn_generated_date = fields.Datetime(string='Generated Date', readonly=True)
    
    qr_code = fields.Binary(string='QR Code', compute='_compute_qr_code', store=True, attachment=True)
    
    sn_move_ids = fields.One2many('brodher.sn.move', 'serial_number_id', string='Move History')
    last_sn_move_date = fields.Datetime(string='Last Move Date')
    
    @api.depends('name')
    def _compute_qr_code(self):
        for record in self:
            if record.name:
                try:
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(record.name)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    record.qr_code = base64.b64encode(buffer.getvalue())
                except Exception as e:
                    _logger.error('QR Code error for %s: %s' % (record.name, str(e)))
                    record.qr_code = False
            else:
                record.qr_code = False
    
    @api.model
    def _get_next_sequence(self, sn_type, year_code, product_id):
        last_sn = self.search([
            ('sn_type', '=', sn_type),
            ('year_code', '=', year_code),
            ('name', 'like', f'PF{year_code}{sn_type}%'),
            ('product_id', '=', product_id)
        ], order='sequence_number desc', limit=1)
        return (last_sn.sequence_number + 1) if last_sn and last_sn.sequence_number else 1
    
    @api.model
    def generate_serial_numbers(self, product_tmpl_id, product_id, sn_type, quantity=1):
        _logger.info('=== Brodher: Generate Serial Numbers ===')
        product_tmpl = self.env['product.template'].browse(product_tmpl_id)
        if not product_tmpl:
            raise ValidationError(_('Product not found!'))
        
        if product_id:
            product = self.env['product.product'].browse(product_id)
        else:
            product = product_tmpl.product_variant_ids[0] if product_tmpl.product_variant_ids else False
        
        if not product:
            raise ValidationError(_('Product variant not found!'))
        if product.tracking != 'serial':
            raise ValidationError(_('Product must have tracking by Serial Number!'))
        
        current_year = datetime.now().strftime('%y')
        serial_numbers = []
        
        for i in range(quantity):
            next_seq = self._get_next_sequence(sn_type, current_year, product.id)
            sn_name = f"PF{current_year}{sn_type}{next_seq:07d}"
            
            if self.search([('name', '=', sn_name), ('product_id', '=', product.id)], limit=1):
                _logger.warning('SN %s exists! Skipping...' % sn_name)
                continue
            
            try:
                sn_record = self.create({
                    'name': sn_name,
                    'product_id': product.id,
                    'company_id': self.env.company.id,
                    'sn_type': sn_type,
                    'year_code': current_year,
                    'sequence_number': next_seq,
                    'sn_status': 'available',
                    'qc_passed': True,
                    'sn_generated_date': fields.Datetime.now(),
                })
                serial_numbers.append(sn_record)
                _logger.info('✓ Created: %s' % sn_name)
            except Exception as e:
                _logger.error('✗ Failed %s: %s' % (sn_name, str(e)))
                continue
        
        return serial_numbers
    
    def action_print_qr_labels(self):
        return self.env.ref('brodher_product_serial.action_report_sn_qr_labels').report_action(self)
    
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.sn_type:
                name += f" ({'Man' if record.sn_type == 'M' else 'Woman'})"
            if record.sn_status:
                name += f" [{record.sn_status.upper()}]"
            result.append((record.id, name))
        return result