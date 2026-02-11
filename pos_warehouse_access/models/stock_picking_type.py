# -*- coding: utf-8 -*-

from odoo import models, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search to filter picking types based on warehouse access"""
        # Check if user is Stock Manager or Admin
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                args = ['&', ('warehouse_id', 'in', allowed_warehouse_ids)] + args
            else:
                # No access to any warehouse
                args = [('id', 'in', [])] + args
        
        return super(StockPickingType, self).search(
            args, offset=offset, limit=limit, order=order
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to filter picking types based on warehouse access"""
        if domain is None:
            domain = []
        
        # Check if user is Stock Manager or Admin
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                domain = ['&', ('warehouse_id', 'in', allowed_warehouse_ids)] + domain
            else:
                # No access to any warehouse
                domain = [('id', 'in', [])] + domain
        
        return super(StockPickingType, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override web_search_read for kanban dashboard"""
        if domain is None:
            domain = []
        
        # Check if user is Stock Manager or Admin  
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                domain = ['&', ('warehouse_id', 'in', allowed_warehouse_ids)] + domain
            else:
                # No access to any warehouse
                domain = [('id', 'in', [])] + domain
        
        return super(StockPickingType, self).web_search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )
