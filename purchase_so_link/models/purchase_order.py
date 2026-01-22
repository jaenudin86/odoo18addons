# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
        tracking=True,
        domain=[('state', 'in', ['sale', 'done'])],
        help='Select the Sales Order related to this purchase'
    )
    
    sale_order_amount = fields.Monetary(
        related='sale_order_id.amount_total',
        string='SO Total Amount',
        store=True
    )
    
    total_po_for_so = fields.Monetary(
        string='Total PO for SO',
        compute='_compute_total_po_for_so',
        store=True,
        help='Total amount of all confirmed PO for this SO'
    )
    
    remaining_so_amount = fields.Monetary(
        string='Remaining SO Amount',
        compute='_compute_remaining_so_amount',
        store=True,
        help='Remaining amount available in SO'
    )
    
    @api.depends('sale_order_id', 'amount_total', 'state')
    def _compute_total_po_for_so(self):
        for order in self:
            if order.sale_order_id:
                # Get all confirmed POs for this SO except current draft
                domain = [
                    ('sale_order_id', '=', order.sale_order_id.id),
                    ('state', 'in', ['purchase', 'done'])
                ]
                if order.state == 'draft' and order.id:
                    domain.append(('id', '!=', order.id))
                
                po_orders = self.search(domain)
                order.total_po_for_so = sum(po_orders.mapped('amount_total'))
            else:
                order.total_po_for_so = 0.0
    
    @api.depends('sale_order_id', 'amount_total', 'total_po_for_so')
    def _compute_remaining_so_amount(self):
        for order in self:
            if order.sale_order_id:
                order.remaining_so_amount = order.sale_order_amount - order.total_po_for_so
            else:
                order.remaining_so_amount = 0.0
    
    @api.constrains('sale_order_id', 'amount_total', 'state')
    def _check_so_amount_limit(self):
        for order in self:
            if order.sale_order_id and order.state in ['purchase', 'done']:
                # Calculate total including current PO
                total_po = order.total_po_for_so + order.amount_total
                
                if total_po > order.sale_order_amount:
                    raise ValidationError(_(
                        'Total Purchase Order amount (%(total_po)s) exceeds Sales Order amount (%(so_amount)s)!\n\n'
                        'Sales Order: %(so_name)s\n'
                        'SO Amount: %(so_amount)s\n'
                        'Previous PO Total: %(prev_po)s\n'
                        'Current PO: %(current_po)s\n'
                        'Total PO: %(total_po)s\n'
                        'Exceeded by: %(exceeded)s'
                    ) % {
                        'total_po': order.currency_id.format(total_po),
                        'so_amount': order.currency_id.format(order.sale_order_amount),
                        'so_name': order.sale_order_id.name,
                        'prev_po': order.currency_id.format(order.total_po_for_so),
                        'current_po': order.currency_id.format(order.amount_total),
                        'exceeded': order.currency_id.format(total_po - order.sale_order_amount),
                    })
    
    def button_confirm(self):
        # Check amount before confirming
        self._check_so_amount_limit()
        return super(PurchaseOrder, self).button_confirm()
    
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if self.sale_order_id:
            # Update partner from SO
            if not self.partner_id:
                self.partner_id = self.sale_order_id.partner_id
