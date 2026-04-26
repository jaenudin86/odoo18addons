# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    decimal_places = fields.Integer(compute='_compute_decimal_places', store=True, readonly=False)

    @api.depends('rounding')
    def _compute_decimal_places(self):
        for currency in self:
            if currency.name == 'IDR':
                currency.decimal_places = 2
            else:
                currency.decimal_places = 3

    def _force_decimal_precision(self):
        """Fungsi untuk memaksa presisi desimal mata uang dan pembulatan."""
        for currency in self:
            if currency.name == 'IDR':
                currency.write({'rounding': 0.01, 'decimal_places': 2})
            else:
                currency.write({'rounding': 0.001, 'decimal_places': 3})
        
        # Paksa juga Decimal Accuracy untuk harga agar mengikuti mata uang
        # Ini biasanya untuk Product Price, Purchase Price, dll
        accuracies = self.env['decimal.precision'].search([
            ('name', 'in', ['Product Price', 'Purchase Price', 'Account'])
        ])
        for acc in accuracies:
            acc.digits = 3 # Kita set ke 3 agar bisa menampung mata uang asing

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') == 'IDR':
                vals['rounding'] = 0.01
                vals['decimal_places'] = 2
            else:
                vals['rounding'] = 0.001
                vals['decimal_places'] = 3
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'rounding' in vals or 'name' in vals:
            # Cegah perubahan manual yang tidak sesuai aturan
            for currency in self:
                if currency.name == 'IDR' and currency.rounding != 0.01:
                    currency.rounding = 0.01
                elif currency.name != 'IDR' and currency.rounding != 0.001:
                    currency.rounding = 0.001
        return res


    @api.model
    def _init_currency_precision(self):
        """
        Method ini bisa dipanggil secara manual atau saat instalasi 
        untuk memperbaiki mata uang yang sudah ada.
        """
        all_currencies = self.search([])
        all_currencies._force_decimal_precision()
