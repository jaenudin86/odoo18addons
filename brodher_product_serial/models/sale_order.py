# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        has_sn_product = any(
            line.product_id.product_tmpl_id.sn_product_type 
            for line in self.order_line
        )
        if has_sn_product:
            message = _(
                'This Sales Order contains products with Serial Numbers. '
                'Please scan Serial Numbers during delivery.'
            )
            self.message_post(body=message, message_type='notification')
        return res