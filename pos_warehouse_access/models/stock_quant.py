# -*- coding: utf-8 -*-

from odoo import models, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to filter stock based on warehouse access"""
        if domain is None:
            domain = []
        
        # Check if user is Stock Manager or Admin
        if not self.env.user.has_group('stock.group_stock_manager') and \
           not self.env.user.has_group('base.group_system'):
            # Regular user - filter by warehouse access
            allowed_warehouse_ids = self.env.user.warehouse_access_ids.ids
            if allowed_warehouse_ids:
                # Get all locations for allowed warehouses
                allowed_locations = self.env['stock.location'].search([
                    ('warehouse_id', 'in', allowed_warehouse_ids)
                ]).ids
                
                if allowed_locations:
                    domain = ['&', ('location_id', 'in', allowed_locations)] + domain
                else:
                    # No locations found for warehouses
                    domain = [('id', '=', False)] + domain
            else:
                # No access to any warehouse
                domain = [('id', '=', False)] + domain
        
        return super(StockQuant, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )
