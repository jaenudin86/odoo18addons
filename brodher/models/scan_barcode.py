# models/scan_barcode.py
from odoo import models, fields, api

class ScanBarcode(models.TransientModel):
    _name = 'brodher.scan.barcode'
    _description = 'Scan Barcode'

    barcode = fields.Char(string="Barcode")
    name = fields.Char(string="Product Name", readonly=True)
    default_code = fields.Char(string="Nomor Artikel", readonly=True)
    brand_id = fields.Many2one('product.brand', string="Brand", readonly=True)
    list_price = fields.Float(string="Price", readonly=True)
    size = fields.Char(string="Size", readonly=True)
    ingredient = fields.Text(string="Ingredient", readonly=True)

    def action_scan(self):
        product = self.env['product.template'].search([('barcode', '=', self.barcode)], limit=1)
        if product:
            self.name = product.name
            self.default_code = product.default_code
            self.brand_id = product.brand_id.id
            self.list_price = product.list_price
            self.size = product.size
            self.ingredient = product.ingredient
        else:
            self.name = "Product not found"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'brodher.scan.barcode',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
