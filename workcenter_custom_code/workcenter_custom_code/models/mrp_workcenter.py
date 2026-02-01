# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    # Field untuk Tujuan (default EQT)
    tujuan = fields.Char(
        string='Tujuan',
        default='EQT',
        required=True,
        readonly=True,
        help='Company/Equipment code (Default: EQT)'
    )
    
    # Field untuk ID Divisi
    division_id = fields.Char(
        string='ID DIVISI',
        required=True,
        size=3,
        help='Division ID (3 characters): OFF, MFR, FN1, FN2, etc.'
    )
    
    # Field untuk Nomor Divisi
    divisi = fields.Char(
        string='DIVISI',
        help='Division number: 1, 2, 3, 12.1, 12.2, etc.'
    )
    
    # Field untuk Nama Devisi
    devisi = fields.Char(
        string='Devisi',
        required=True,
        help='Division name: Sales, Marketing, Production, etc.'
    )
    
    # Override field code
    code = fields.Char(
        string='Code',
        compute='_compute_workcenter_code',
        store=True,
        readonly=True,
        help='Auto-generated code format: EQT.[DEPT].[CODE].00000'
    )
    
    # Field untuk department type
    department_type = fields.Selection([
        ('office', 'Office (OFF)'),
        ('manufacturing', 'Manufacturing (MFR)')
    ], string='Department Type', required=True, default='office',
       help='Office for non-production, Manufacturing for production')
    
    # Field untuk short code (3 huruf)
    short_code = fields.Char(
        string='Short Code',
        size=3,
        required=True,
        help='3-letter code for work center: SLS, MRK, FRD, MCH, etc.'
    )
    
    # Field untuk sequence number
    sequence_number = fields.Char(
        string='Sequence',
        default='00000',
        size=5,
        help='5-digit sequence number'
    )

    @api.depends('tujuan', 'department_type', 'short_code', 'sequence_number')
    def _compute_workcenter_code(self):
        """
        Auto-generate work center code
        Format: EQT.OFF.SLS.00000 or EQT.MFR.FRD.00000
        """
        for record in self:
            if record.department_type and record.short_code:
                dept_code = 'OFF' if record.department_type == 'office' else 'MFR'
                sequence = record.sequence_number or '00000'
                record.code = f"{record.tujuan}.{dept_code}.{record.short_code.upper()}.{sequence}"
            else:
                record.code = False

    @api.constrains('short_code')
    def _check_short_code(self):
        """Validate short code is exactly 3 characters"""
        for record in self:
            if record.short_code and len(record.short_code) != 3:
                raise UserError(_('Short Code must be exactly 3 characters!'))

    @api.constrains('sequence_number')
    def _check_sequence_number(self):
        """Validate sequence number is exactly 5 digits"""
        for record in self:
            if record.sequence_number:
                if len(record.sequence_number) != 5 or not record.sequence_number.isdigit():
                    raise UserError(_('Sequence number must be exactly 5 digits!'))

    @api.model
    def create(self, vals):
        """Override create to ensure code generation"""
        # Auto uppercase short_code
        if vals.get('short_code'):
            vals['short_code'] = vals['short_code'].upper()
        
        # Set default sequence if not provided
        if not vals.get('sequence_number'):
            vals['sequence_number'] = '00000'
            
        return super(MrpWorkcenter, self).create(vals)

    def write(self, vals):
        """Override write to ensure code updates"""
        # Auto uppercase short_code
        if vals.get('short_code'):
            vals['short_code'] = vals['short_code'].upper()
            
        return super(MrpWorkcenter, self).write(vals)

    @api.onchange('devisi')
    def _onchange_devisi_suggest_short_code(self):
        """Suggest short code based on devisi name"""
        if self.devisi and not self.short_code:
            # Simple suggestion: take first 3 letters
            suggestion = ''.join(filter(str.isalpha, self.devisi))[:3].upper()
            if len(suggestion) == 3:
                self.short_code = suggestion

    @api.onchange('department_type')
    def _onchange_department_type(self):
        """Update division_id based on department type"""
        if self.department_type == 'office':
            if not self.division_id or self.division_id == 'MFR':
                self.division_id = 'OFF'
        elif self.department_type == 'manufacturing':
            if not self.division_id or self.division_id == 'OFF':
                self.division_id = 'MFR'
