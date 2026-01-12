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
    def _get_next_sequence_global(self, sn_type, year):
        """
        Get next GLOBAL sequence number across ALL products
        Only resets when:
        - Different type (M/W)
        - Different year
        
        Continues for different products/variants
        """
        # Search for ANY product with this year and type
        domain = [
            ('name', 'like', f'PF{year}{sn_type}%')
            # NO product_id filter - GLOBAL across all products
        ]
        
        last_sn = self.search(domain, order='name desc', limit=1)
        
        if last_sn:
            # Extract sequence from last SN (PFYYTXXXXXXX -> XXXXXXX)
            sequence_str = last_sn.name[-7:]
            next_sequence = int(sequence_str) + 1
            _logger.info(f'GLOBAL sequence for {year}{sn_type}: continuing from {sequence_str} to {next_sequence}')
            return next_sequence
        else:
            _logger.info(f'GLOBAL sequence for {year}{sn_type}: starting from 1')
            return 1


    def generate_serial_numbers(self, product_tmpl_id, product_id, sn_type, quantity):
        """
        Generate serial numbers with GLOBAL sequence
        """
        if quantity <= 0:
            raise UserError(_('Quantity must be greater than 0'))
        
        year = datetime.now().strftime('%y')
        serial_numbers = []
        
        # Get starting sequence GLOBALLY
        next_seq = self._get_next_sequence_global(sn_type, year)
        
        _logger.info(f'Generating {quantity} SNs for product_id={product_id}, type={sn_type}, starting from seq={next_seq}')
        
        for i in range(quantity):
            current_seq = next_seq + i
            sn_name = f"PF{year}{sn_type}{current_seq:07d}"
            
            # Check if SN already exists
            existing = self.search([('name', '=', sn_name)], limit=1)
            if existing:
                _logger.warning(f'SN {sn_name} already exists, skipping...')
                continue
            
            # Create new serial number
            sn = self.create({
                'name': sn_name,
                'product_id': product_id,
                'company_id': self.env.company.id,
            })
            serial_numbers.append(sn)
            _logger.info(f'Created SN: {sn_name} for product_id={product_id}')
        
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