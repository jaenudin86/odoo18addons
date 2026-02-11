# -*- coding: utf-8 -*-

from odoo import models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search to filter pickings based on warehouse access"""
        # Check if user is Stock Manager or Admin
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                # Filter by picking type's warehouse
                allowed_picking_types = self.env['stock.picking.type'].search([
                    ('warehouse_id', 'in', allowed_warehouse_ids)
                ]).ids
                
                if allowed_picking_types:
                    # Add filter
                if args:
                    args = ['&', ('picking_type_id', 'in', allowed_picking_types)] + domain
                else:
                    args = [('picking_type_id', 'in', allowed_picking_types)]
                else:
                    args = [('id', '=', False)] + domain
            else:
                # No access to any warehouse
                args = [('id', '=', False)] + domain
        
        return super(StockPicking, self).search(
            domain, offset=offset, limit=limit, order=order, count=count
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to filter pickings based on warehouse access"""
        if domain is None:
            args = []
        
        # Check if user is Stock Manager or Admin
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                # Filter by picking type's warehouse
                allowed_picking_types = self.env['stock.picking.type'].search([
                    ('warehouse_id', 'in', allowed_warehouse_ids)
                ]).ids
                
                if allowed_picking_types:
                    # Add filter
                if args:
                    args = ['&', ('picking_type_id', 'in', allowed_picking_types)] + domain
                else:
                    args = [('picking_type_id', 'in', allowed_picking_types)]
                else:
                    args = [('id', '=', False)] + domain
            else:
                # No access to any warehouse
                args = [('id', '=', False)] + domain
        
        return super(StockPicking, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )
