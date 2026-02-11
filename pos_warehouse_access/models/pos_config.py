# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    user_access_ids = fields.Many2many(
        'res.users',
        'pos_user_access_rel',
        'pos_id',
        'user_id',
        string='User Access',
        help='User yang bisa mengakses POS ini'
    )
    
    user_access_count = fields.Integer(
        string='User Access Count',
        compute='_compute_user_access_count'
    )
    
    @api.depends('user_access_ids')
    def _compute_user_access_count(self):
        for pos in self:
            pos.user_access_count = len(pos.user_access_ids)
    
    # No search override - rely on record rules only
