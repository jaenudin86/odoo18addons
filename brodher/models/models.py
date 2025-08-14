# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class brodher(models.Model):
#     _name = 'brodher.brodher'
#     _description = 'brodher.brodher'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ingredients = fields.Text(string="Ingredients")
    brand = fields.Char(string="Brand")
    size = fields.Char(string="Size")


        