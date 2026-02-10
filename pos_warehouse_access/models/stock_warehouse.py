# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    user_access_ids = fields.Many2many(
        'res.users',
        'warehouse_user_access_rel',
        'warehouse_id',
        'user_id',
        string='User Access',
        help='User yang bisa melihat gudang ini'
    )
    
    user_access_count = fields.Integer(
        string='User Access Count',
        compute='_compute_user_access_count'
    )
    
    @api.depends('user_access_ids')
    def _compute_user_access_count(self):
        for warehouse in self:
            warehouse.user_access_count = len(warehouse.user_access_ids)
    
    def action_view_user_access(self):
        """Open list view of users that can access this warehouse"""
        self.ensure_one()
        return {
            'name': 'User Access',
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.user_access_ids.ids)],
            'context': {'default_warehouse_access_ids': [(4, self.id)]},
        }
