# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection(selection_add=[('closed', 'Closed')], ondelete={'closed': 'set default'})
    
    def action_close_po(self):
        for order in self:
            if order.state == 'purchase':
                # Cancel associated pickings that are not finished
                pickings_to_cancel = order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                if pickings_to_cancel:
                    pickings_to_cancel.action_cancel()
                    order.message_post(body=_("Associated transfers %s have been cancelled due to PO closure.") % 
                                       (", ".join(pickings_to_cancel.mapped('name'))))
                
                order.write({'state': 'closed'})

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