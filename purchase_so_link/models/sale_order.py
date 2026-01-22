# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'sale_order_id',
        string='Purchase Orders',
        help='Purchase Orders linked to this Sales Order'
    )
    
    purchase_order_count = fields.Integer(
        string='PO Count',
        compute='_compute_purchase_order_count'
    )
    
    total_purchase_amount = fields.Monetary(
        string='Total Purchase Amount',
        compute='_compute_total_purchase_amount',
        store=True
    )
    
    remaining_purchase_budget = fields.Monetary(
        string='Remaining Budget',
        compute='_compute_remaining_purchase_budget',
        store=True
    )
    
    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for order in self:
            order.purchase_order_count = len(order.purchase_order_ids)
    
    @api.depends('purchase_order_ids.amount_total', 'purchase_order_ids.state')
    def _compute_total_purchase_amount(self):
        for order in self:
            confirmed_pos = order.purchase_order_ids.filtered(
                lambda po: po.state in ['purchase', 'done']
            )
            order.total_purchase_amount = sum(confirmed_pos.mapped('amount_total'))
    
    @api.depends('amount_total', 'total_purchase_amount')
    def _compute_remaining_purchase_budget(self):
        for order in self:
            order.remaining_purchase_budget = order.amount_total - order.total_purchase_amount
    
    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id}
        }
