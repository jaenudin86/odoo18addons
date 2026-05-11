# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    woo_order_id = fields.Char('WooCommerce Order ID', copy=False, index=True)
    woo_backend_id = fields.Many2one('woo.backend', string='WooCommerce Instance', copy=False)

    def action_confirm(self):
        """Sync status to WooCommerce on confirmation."""
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if order.woo_backend_id and order.woo_order_id:
                order.action_woo_update_status('completed') # or 'processing'
        return res

    def action_woo_update_status(self, status):
        """Update order status in WooCommerce."""
        self.ensure_one()
        if not self.woo_backend_id or not self.woo_order_id:
            return
            
        wcapi = self.woo_backend_id.get_woo_api()
        data = {"status": status}
        try:
            response = wcapi.put("orders/%s" % self.woo_order_id, data)
            if response.status_code != 200:
                self.env['woo.sync.log'].create({
                    'backend_id': self.woo_backend_id.id,
                    'operation': 'export',
                    'resource': 'order',
                    'state': 'failed',
                    'message': "Failed to update status to %s: %s" % (status, response.text)
                })
        except Exception as e:
            self.env['woo.sync.log'].create({
                'backend_id': self.woo_backend_id.id,
                'operation': 'export',
                'resource': 'order',
                'state': 'failed',
                'message': "Error updating status: %s" % str(e)
            })
