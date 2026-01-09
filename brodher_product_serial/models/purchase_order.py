# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        has_sn_product = any(
            line.product_id.product_tmpl_id.sn_product_type 
            for line in self.order_line
        )
        if has_sn_product:
            message = _(
                'This Purchase Order contains products with Serial Numbers. '
                'Please scan Serial Numbers during receipt.'
            )
            self.message_post(body=message, message_type='notification')
        return res