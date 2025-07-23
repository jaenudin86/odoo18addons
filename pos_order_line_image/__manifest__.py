# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Bhagyadev KP (odoo@cybrosys.com)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
################################################################################
{
    'name': "Pos Order Line Product Image",
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': """Product image in pos order lines""",
    'description': "By default, odoo doesn't support showing product images"
                   " in each line of the order list. This module Helps to "
                   "show product images in each order line.",
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "http://www.cybrosys.com",
    'depends': ['point_of_sale'],
    'assets': {
            'point_of_sale._assets_pos': [
                'pos_order_line_image/static/src/css/order_line_image.css',
                'pos_order_line_image/static/src/xml/pos_order_line.xml',
                'pos_order_line_image/static/src/js/pos_order_line.js'
            ],
    },
    'images': ['static/description/banner.png'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
