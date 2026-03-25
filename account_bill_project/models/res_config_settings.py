# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    director_approval_limit = fields.Float(
        string='Batas Nilai Persetujuan Direktur (Rp)',
        default=50000000.0,
        config_parameter='account_bill_project.director_approval_limit',
        help='Tagihan di atas nilai ini akan membutuhkan persetujuan Direktur Keuangan.',
    )
