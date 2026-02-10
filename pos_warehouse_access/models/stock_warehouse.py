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
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search to filter warehouses based on user access"""
        # Check if user is Stock Manager or Admin
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                args = ['&', ('id', 'in', allowed_warehouse_ids)] + args
            else:
                # No access to any warehouse
                args = [('id', '=', False)] + args
        
        return super(StockWarehouse, self).search(
            args, offset=offset, limit=limit, order=order
        )
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to filter warehouses based on user access"""
        if domain is None:
            domain = []
        
        # Check if user is Stock Manager or Admin
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                domain = ['&', ('id', 'in', allowed_warehouse_ids)] + domain
            else:
                # No access to any warehouse
                domain = [('id', '=', False)] + domain
        
        return super(StockWarehouse, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )
    
    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override web_search_read for web client kanban/list views"""
        if domain is None:
            domain = []
        
        # Check if user is Stock Manager or Admin  
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                domain = ['&', ('id', 'in', allowed_warehouse_ids)] + domain
            else:
                # No access to any warehouse
                domain = [('id', '=', False)] + domain
        
        return super(StockWarehouse, self).web_search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )
    
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
