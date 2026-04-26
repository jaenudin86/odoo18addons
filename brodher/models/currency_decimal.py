# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    def _force_decimal_precision(self):
        """Fungsi untuk memaksa presisi desimal mata uang."""
        for currency in self:
            if currency.name == 'IDR':
                if currency.rounding != 0.01:
                    currency.rounding = 0.01
            else:
                if currency.rounding != 0.001:
                    currency.rounding = 0.001

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') == 'IDR':
                vals['rounding'] = 0.01
            else:
                vals['rounding'] = 0.001
        return super().create(vals_list)

    def write(self, vals):
        # Jika ada perubahan rounding atau name, kita cek kembali
        res = super().write(vals)
        if 'rounding' in vals or 'name' in vals:
            self._force_decimal_precision()
        return res

    @api.model
    def _init_currency_precision(self):
        """
        Method ini bisa dipanggil secara manual atau saat instalasi 
        untuk memperbaiki mata uang yang sudah ada.
        """
        all_currencies = self.search([])
        all_currencies._force_decimal_precision()
