# -*- coding: utf-8 -*-
from odoo import models, fields, tools


class PurchaseSoReport(models.Model):
    _name = 'purchase.so.report'
    _description = 'Purchase Order by Sales Order Report'
    _auto = False
    _rec_name = 'sale_order_id'

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', readonly=True)
    sale_order_name = fields.Char(string='SO Number', readonly=True)
    sale_order_date = fields.Date(string='SO Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    sale_user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    purchase_order_name = fields.Char(string='PO Number', readonly=True)
    purchase_date = fields.Date(string='PO Date', readonly=True)
    purchase_partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    
    sale_amount = fields.Monetary(string='SO Amount', readonly=True)
    purchase_amount = fields.Monetary(string='PO Amount', readonly=True)
    
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    po.id as id,
                    po.sale_order_id,
                    so.name as sale_order_name,
                    so.date_order as sale_order_date,
                    so.partner_id,
                    so.user_id as sale_user_id,
                    po.id as purchase_order_id,
                    po.name as purchase_order_name,
                    po.date_order as purchase_date,
                    po.partner_id as purchase_partner_id,
                    so.amount_total as sale_amount,
                    po.amount_total as purchase_amount,
                    po.currency_id,
                    po.company_id,
                    po.state
                FROM purchase_order po
                LEFT JOIN sale_order so ON po.sale_order_id = so.id
                WHERE po.sale_order_id IS NOT NULL
            )
        """ % self._table)
