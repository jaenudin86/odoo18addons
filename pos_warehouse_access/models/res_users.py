# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    pos_access_ids = fields.Many2many(
        'pos.config',
        'pos_user_access_rel',
        'user_id',
        'pos_id',
        string='POS Access',
        help='Point of Sale yang bisa diakses user ini'
    )
    
    warehouse_access_ids = fields.Many2many(
        'stock.warehouse',
        'warehouse_user_access_rel',
        'user_id',
        'warehouse_id',
        string='Warehouse Access',
        help='Gudang yang bisa dilihat user ini'
    )
    
    pos_access_count = fields.Integer(
        string='POS Access Count',
        compute='_compute_access_counts'
    )
    
    warehouse_access_count = fields.Integer(
        string='Warehouse Access Count',
        compute='_compute_access_counts'
    )
    
    @api.depends('pos_access_ids', 'warehouse_access_ids')
    def _compute_access_counts(self):
        for user in self:
            user.pos_access_count = len(user.pos_access_ids)
            user.warehouse_access_count = len(user.warehouse_access_ids)
    
    def action_view_pos_access(self):
        """Open list view of POS that user can access"""
        self.ensure_one()
        return {
            'name': 'POS Access',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.config',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.pos_access_ids.ids)],
            'context': {'default_user_access_ids': [(4, self.id)]},
        }
    
    def action_view_warehouse_access(self):
        """Open list view of warehouses that user can access"""
        self.ensure_one()
        return {
            'name': 'Warehouse Access',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.warehouse',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.warehouse_access_ids.ids)],
            'context': {'default_user_access_ids': [(4, self.id)]},
        }
