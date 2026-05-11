# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WooMappingBase(models.AbstractModel):
    _name = 'woo.mapping.base'
    _description = 'WooCommerce Mapping Base'

    backend_id = fields.Many2one('woo.backend', string='Backend', required=True, ondelete='cascade')
    woo_id = fields.Char('WooCommerce ID', required=True)
    last_sync_date = fields.Datetime('Last Sync Date', default=fields.Datetime.now)

class WooProductCategoryMapping(models.Model):
    _name = 'woo.product.category.mapping'
    _inherit = 'woo.mapping.base'
    _description = 'WooCommerce Product Category Mapping'

    odoo_id = fields.Many2one('product.category', string='Odoo Category', required=True, ondelete='cascade')

class WooProductTemplateMapping(models.Model):
    _name = 'woo.product.template.mapping'
    _inherit = 'woo.mapping.base'
    _description = 'WooCommerce Product Template Mapping'

    odoo_id = fields.Many2one('product.template', string='Odoo Template', required=True, ondelete='cascade')

class WooProductProductMapping(models.Model):
    _name = 'woo.product.product.mapping'
    _inherit = 'woo.mapping.base'
    _description = 'WooCommerce Product Variant Mapping'

    odoo_id = fields.Many2one('product.product', string='Odoo Variant', required=True, ondelete='cascade')

class WooProductAttributeMapping(models.Model):
    _name = 'woo.product.attribute.mapping'
    _inherit = 'woo.mapping.base'
    _description = 'WooCommerce Product Attribute Mapping'

    odoo_id = fields.Many2one('product.attribute', string='Odoo Attribute', required=True, ondelete='cascade')

class WooProductAttributeValueMapping(models.Model):
    _name = 'woo.product.attribute.value.mapping'
    _inherit = 'woo.mapping.base'
    _description = 'WooCommerce Product Attribute Value Mapping'

    odoo_id = fields.Many2one('product.attribute.value', string='Odoo Attribute Value', required=True, ondelete='cascade')

class WooPaymentGatewayMapping(models.Model):
    _name = 'woo.payment.gateway.mapping'
    _inherit = 'woo.mapping.base'
    _description = 'WooCommerce Payment Gateway Mapping'

    name = fields.Char('Gateway Name')
    odoo_journal_id = fields.Many2one('account.journal', string='Odoo Journal', ondelete='cascade')

class WooTaxMapping(models.Model):
    _name = 'woo.tax.mapping'
    _inherit = 'woo.mapping.base'
    _description = 'WooCommerce Tax Mapping'

    odoo_tax_id = fields.Many2one('account.tax', string='Odoo Tax', ondelete='cascade')
