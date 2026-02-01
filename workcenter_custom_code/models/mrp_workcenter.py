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
    
    # Field Selection untuk Division (hardcoded dari Excel)
    division_master = fields.Selection([
        # OFFICE DEPARTMENTS
        ('sales', 'Sales'),
        ('marketing', 'Marketing'),
        ('keuangan1', 'Keuangan 1'),
        ('keuangan2', 'Keuangan 2'),
        ('keuangan3', 'Keuangan 3'),
        ('design', 'Design & Drawing'),
        ('rnd', 'RnD'),
        ('product_app', 'Product Application'),
        ('planner', 'Planner & PPC'),
        ('project_est', 'Project Estimator'),
        ('mfr_seca', 'MFR Seca & PPC'),
        # PRODUCTION
        ('production', 'Production'),
        ('foundry', 'Foundry'),
        ('machining', 'Machining'),
        ('painting', 'Painting'),
        ('assembly', 'Assembly'),
        ('testing', 'Testing'),
        ('packing', 'Packing'),
        # SUPPORT
        ('shipping', 'Shipping & Expedating'),
        ('cs', 'CS'),
        ('quality', 'Quality'),
        ('safety', 'Safety'),
        ('mdr', 'MDR & Docen'),
    ], string='Division', required=True, help='Pilih divisi dari list')
    
    # Field untuk ID Divisi (computed dari division_master)
    division_id = fields.Char(
        string='ID DIVISI',
        compute='_compute_division_fields',
        store=True,
        help='Division ID (3 characters): OFF, MFR, FN1, FN2, etc.'
    )
    
    # Field untuk Nomor Divisi (computed dari division_master)
    divisi = fields.Char(
        string='DIVISI',
        compute='_compute_division_fields',
        store=True,
        help='Division number: 1, 2, 3, 12.1, 12.2, etc.'
    )
    
    # Field untuk Nama Devisi (computed dari division_master)
    devisi = fields.Char(
        string='Devisi',
        compute='_compute_division_fields',
        store=True,
        help='Division name: Sales, Marketing, Production, etc.'
    )
    
    # Field untuk department type (computed dari division_master)
    department_type = fields.Selection([
        ('office', 'Office (OFF)'),
        ('manufacturing', 'Manufacturing (MFR)')
    ], string='Department Type',
       compute='_compute_division_fields',
       store=True,
       help='Office for non-production, Manufacturing for production')
    
    # Field untuk short code (computed dari division_master)
    short_code = fields.Char(
        string='Short Code',
        compute='_compute_division_fields',
        store=True,
        help='3-letter code for work center: SLS, MRK, FRD, MCH, etc.'
    )
    
    # Override field code
    code = fields.Char(
        string='Code',
        compute='_compute_workcenter_code',
        store=True,
        readonly=True,
        help='Auto-generated code format: EQT.[DEPT].[CODE].00000'
    )
    
    # Field untuk sequence number (manual input)
    sequence_number = fields.Char(
        string='Sequence',
        default='00000',
        size=5,
        help='5-digit sequence number (manual input for unique code)'
    )

    # Mapping data divisi (hardcoded dari Excel)
    _DIVISION_DATA = {
        # format: 'key': (division_id, divisi_number, devisi_name, dept_type, short_code)
        'sales': ('OFF', '1', 'Sales', 'office', 'SLS'),
        'marketing': ('MFR', '2', 'Marketing', 'office', 'MRK'),
        'keuangan1': ('FN1', '3', 'Keuangan 1', 'office', 'FN1'),
        'keuangan2': ('FN2', '4', 'Keuangan 2', 'office', 'FN2'),
        'keuangan3': ('FN3', '5', 'Keuangan 3', 'office', 'FN3'),
        'design': ('DNC', '6', 'Design & Drawing', 'office', 'DND'),
        'rnd': ('RND', '7', 'RnD', 'office', 'RND'),
        'product_app': ('PAP', '8', 'Product Application', 'office', 'PAP'),
        'planner': ('PLP', '9', 'Planner & PPC', 'office', 'PLP'),
        'project_est': ('PST', '10', 'Project Estimator', 'office', 'PST'),
        'mfr_seca': ('PPC', '11', 'MFR Seca & PPC', 'office', 'PPC'),
        'production': ('PRD', '12', 'Production', 'manufacturing', 'PRD'),
        'foundry': ('FRD', '12.1', 'Foundry', 'manufacturing', 'FRD'),
        'machining': ('MCH', '12.2', 'Machining', 'manufacturing', 'MCH'),
        'painting': ('PNT', '12.3', 'Painting', 'manufacturing', 'PNT'),
        'assembly': ('ASY', '12.4', 'Assembly', 'manufacturing', 'ASY'),
        'testing': ('TST', '12.5', 'Testing', 'manufacturing', 'TST'),
        'packing': ('PCK', '12.6', 'Packing', 'manufacturing', 'PCK'),
        'shipping': ('SNC', '13', 'Shipping & Expedating', 'office', 'SNE'),
        'cs': ('CSR', '14', 'CS', 'office', 'CSR'),
        'quality': ('QAL', '15', 'Quality', 'office', 'QAL'),
        'safety': ('SFT', '16', 'Safety', 'office', 'SFT'),
        'mdr': ('MDC', '17', 'MDR & Docen', 'office', 'MDC'),
    }

    @api.depends('division_master')
    def _compute_division_fields(self):
        """Compute division fields based on selected division_master"""
        for record in self:
            if record.division_master and record.division_master in self._DIVISION_DATA:
                data = self._DIVISION_DATA[record.division_master]
                record.division_id = data[0]
                record.divisi = data[1]
                record.devisi = data[2]
                record.department_type = data[3]
                record.short_code = data[4]
            else:
                record.division_id = False
                record.divisi = False
                record.devisi = False
                record.department_type = False
                record.short_code = False

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
                record.code = f"{record.tujuan}.{dept_code}.{record.short_code}.{sequence}"
            else:
                record.code = False

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
        # Set default sequence if not provided
        if not vals.get('sequence_number'):
            vals['sequence_number'] = '00000'
            
        return super(MrpWorkcenter, self).create(vals)

    @api.constrains('division_master', 'sequence_number')
    def _check_unique_code(self):
        """Check if generated code is unique"""
        for record in self:
            if record.division_master and record.sequence_number:
                domain = [
                    ('id', '!=', record.id),
                    ('division_master', '=', record.division_master),
                    ('sequence_number', '=', record.sequence_number)
                ]
                if self.search_count(domain) > 0:
                    raise UserError(_(
                        'Work Center code must be unique!\n'
                        'Division "%s" with sequence "%s" already exists.'
                    ) % (record.devisi, record.sequence_number))
