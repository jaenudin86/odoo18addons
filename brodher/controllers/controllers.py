# -*- coding: utf-8 -*-
# from odoo import http


# class Brodher(http.Controller):
#     @http.route('/brodher/brodher', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/brodher/brodher/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('brodher.listing', {
#             'root': '/brodher/brodher',
#             'objects': http.request.env['brodher.brodher'].search([]),
#         })

#     @http.route('/brodher/brodher/objects/<model("brodher.brodher"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('brodher.object', {
#             'object': obj
#         })

