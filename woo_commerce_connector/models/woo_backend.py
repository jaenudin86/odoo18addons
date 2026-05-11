# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    from woocommerce import API
except ImportError:
    _logger.error("The 'woocommerce' python library is not installed.")

class WooBackend(models.Model):
    _name = 'woo.backend'
    _description = 'WooCommerce Backend'

    name = fields.Char('Instance Name', required=True)
    woo_url = fields.Char('Store URL', required=True, help="Example: https://yourstore.com")
    woo_consumer_key = fields.Char('Consumer Key', required=True)
    woo_consumer_secret = fields.Char('Consumer Secret', required=True)
    
    # Defaults
    warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist', required=True)
    sales_team_id = fields.Many2one('crm.team', string='Sales Team')
    
    # Sync Flags
    auto_import_products = fields.Boolean('Auto Import Products', default=False)
    auto_import_orders = fields.Boolean('Auto Import Orders', default=False)
    auto_export_stock = fields.Boolean('Auto Export Stock', default=False)
    
    # Dashboard Stats
    total_products = fields.Integer(compute='_compute_stats')
    total_orders = fields.Integer(compute='_compute_stats')
    total_revenue = fields.Float(compute='_compute_stats')

    def _compute_stats(self):
        """Compute statistics for the dashboard."""
        for backend in self:
            backend.total_products = self.env['woo.product.template.mapping'].search_count([('backend_id', '=', backend.id)])
            orders = self.env['sale.order'].search([('woo_backend_id', '=', backend.id)])
            backend.total_orders = len(orders)
            backend.total_revenue = sum(orders.mapped('amount_total'))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Connected'),
        ('error', 'Error')
    ], default='draft', string='Status')

    def get_woo_api(self):
        """Helper to initialize WooCommerce API."""
        self.ensure_one()
        try:
            wcapi = API(
                url=self.woo_url,
                consumer_key=self.woo_consumer_key,
                consumer_secret=self.woo_consumer_secret,
                version="wc/v3",
                timeout=30
            )
            return wcapi
        except Exception as e:
            raise UserError(_("Failed to connect to WooCommerce: %s") % str(e))

    def action_test_connection(self):
        """Test connection to WooCommerce."""
        for backend in self:
            wcapi = backend.get_woo_api()
            try:
                # Try to get system info or a simple product list
                response = wcapi.get("products", params={"per_page": 1})
                if response.status_code == 200:
                    backend.state = 'confirmed'
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'message': _('Connection successful!'),
                            'type': 'success',
                        }
                    }
                else:
                    backend.state = 'error'
                    raise UserError(_("Connection failed (Code %s): %s") % (response.status_code, response.text))
            except Exception as e:
                backend.state = 'error'
                raise UserError(_("Connection Error: %s") % str(e))

    def action_open_operations(self):
        """Open wizard for manual operations."""
        self.ensure_one()
        return {
            'name': _('WooCommerce Operations'),
            'type': 'ir.actions.act_window',
            'res_model': 'woo.operation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_backend_id': self.id}
        }

    def action_register_webhooks(self):
        """Register webhooks in WooCommerce."""
        self.ensure_one()
        wcapi = self.get_woo_api()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        webhook_url = "%s/woo_connector/webhook/%s" % (base_url, self.id)
        
        data = {
            "name": "Odoo Order Created",
            "topic": "order.created",
            "delivery_url": webhook_url,
            "status": "active"
        }
        try:
            response = wcapi.post("webhooks", data)
            if response.status_code == 201:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Webhook registered successfully!'),
                        'type': 'success',
                    }
                }
            else:
                raise UserError(_("Failed to register webhook: %s") % response.text)
        except Exception as e:
            raise UserError(_("Webhook Error: %s") % str(e))

    @api.model
    def _cron_auto_import_orders(self):
        """Cron job to import orders for all active backends."""
        backends = self.search([('state', '=', 'confirmed'), ('auto_import_orders', '=', True)])
        for backend in backends:
            wizard = self.env['woo.operation.wizard'].create({
                'backend_id': backend.id,
                'operation': 'import_order'
            })
            wizard._import_orders()

    @api.model
    def _cron_auto_export_stock(self):
        """Cron job to export stock for all active backends."""
        backends = self.search([('state', '=', 'confirmed'), ('auto_export_stock', '=', True)])
        for backend in backends:
            wizard = self.env['woo.operation.wizard'].create({
                'backend_id': backend.id,
                'operation': 'export_stock'
            })
            wizard._export_stock()
