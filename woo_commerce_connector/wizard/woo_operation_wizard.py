from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import requests
import base64

_logger = logging.getLogger(__name__)

class WooOperationWizard(models.TransientModel):
    _name = 'woo.operation.wizard'
    _description = 'WooCommerce Operation Wizard'

    backend_id = fields.Many2one('woo.backend', string='Backend', required=True)
    operation = fields.Selection([
        ('import_category', 'Import Categories'),
        ('import_attribute', 'Import Attributes'),
        ('import_payment_gateway', 'Import Payment Gateways'),
        ('import_product', 'Import Products'),
        ('export_product', 'Export Products (Odoo -> Woo)'),
        ('import_order', 'Import Orders (Processing)'),
        ('export_stock', 'Export Stock Levels'),
    ], string='Operation', required=True)

    def action_execute(self):
        """Execute selected operation."""
        self.ensure_one()
        if self.operation == 'import_category':
            return self._import_categories()
        elif self.operation == 'import_attribute':
            return self._import_attributes()
        elif self.operation == 'import_payment_gateway':
            return self._import_payment_gateways()
        elif self.operation == 'import_product':
            return self._import_products()
        elif self.operation == 'export_product':
            return self._export_products()
        elif self.operation == 'import_order':
            return self._import_orders()
        elif self.operation == 'export_stock':
            return self._export_stock()
        # Other operations will be implemented in next phases
        return True

    def _import_categories(self):
        """Import categories from WooCommerce and create mappings."""
        wcapi = self.backend_id.get_woo_api()
        page = 1
        total_imported = 0
        
        while True:
            response = wcapi.get("products/categories", params={"per_page": 100, "page": page})
            if response.status_code != 200:
                break
            
            categories = response.json()
            if not categories:
                break
                
            for cat in categories:
                woo_id = str(cat.get('id'))
                name = cat.get('name')
                
                # Check mapping
                mapping = self.env['woo.product.category.mapping'].search([
                    ('backend_id', '=', self.backend_id.id),
                    ('woo_id', '=', woo_id)
                ], limit=1)
                
                if not mapping:
                    # Create Odoo Category
                    odoo_cat = self.env['product.category'].create({'name': name})
                    # Create Mapping
                    self.env['woo.product.category.mapping'].create({
                        'backend_id': self.backend_id.id,
                        'woo_id': woo_id,
                        'odoo_id': odoo_cat.id
                    })
                    total_imported += 1
            
            page += 1
            
        return self._notification(_("Imported %d new categories.") % total_imported)

    def _import_attributes(self):
        """Import attributes from WooCommerce."""
        wcapi = self.backend_id.get_woo_api()
        response = wcapi.get("products/attributes")
        if response.status_code != 200:
            raise UserError(_("Failed to fetch attributes: %s") % response.text)
            
        attributes = response.json()
        total_imported = 0
        
        for attr in attributes:
            woo_id = str(attr.get('id'))
            name = attr.get('name')
            
            mapping = self.env['woo.product.attribute.mapping'].search([
                ('backend_id', '=', self.backend_id.id),
                ('woo_id', '=', woo_id)
            ], limit=1)
            
            if not mapping:
                odoo_attr = self.env['product.attribute'].create({'name': name})
                self.env['woo.product.attribute.mapping'].create({
                    'backend_id': self.backend_id.id,
                    'woo_id': woo_id,
                    'odoo_id': odoo_attr.id
                })
                total_imported += 1
                
        return self._notification(_("Imported %d new attributes.") % total_imported)

    def _import_payment_gateways(self):
        """Import payment gateways from WooCommerce."""
        wcapi = self.backend_id.get_woo_api()
        response = wcapi.get("payment_gateways")
        if response.status_code != 200:
            raise UserError(_("Failed to fetch gateways: %s") % response.text)
            
        gateways = response.json()
        total_imported = 0
        
        for gw in gateways:
            woo_id = str(gw.get('id'))
            name = gw.get('title')
            
            mapping = self.env['woo.payment.gateway.mapping'].search([
                ('backend_id', '=', self.backend_id.id),
                ('woo_id', '=', woo_id)
            ], limit=1)
            
            if not mapping:
                self.env['woo.payment.gateway.mapping'].create({
                    'backend_id': self.backend_id.id,
                    'woo_id': woo_id,
                    'name': name
                })
                total_imported += 1
                
        return self._notification(_("Imported %d new payment gateways.") % total_imported)

    def _import_products(self):
        """
        Import products from WooCommerce.
        Handles Simple and Variable products.
        """
        wcapi = self.backend_id.get_woo_api()
        page = 1
        total_imported = 0
        
        while True:
            params = {"per_page": 20, "page": page}
            response = wcapi.get("products", params=params)
            if response.status_code != 200:
                break
            
            products = response.json()
            if not products:
                break
                
            for product_data in products:
                woo_id = str(product_data.get('id'))
                name = product_data.get('name')
                type = product_data.get('type') # simple, variable, grouped, external
                
                # 1. Check if already mapped
                mapping = self.env['woo.product.template.mapping'].search([
                    ('backend_id', '=', self.backend_id.id),
                    ('woo_id', '=', woo_id)
                ], limit=1)
                
                if mapping:
                    continue
                
                # 2. Get/Create Odoo Template
                template_vals = {
                    'name': name,
                    'type': 'consu' if product_data.get('virtual') else 'product',
                    'list_price': float(product_data.get('regular_price') or 0.0),
                    'default_code': product_data.get('sku'),
                    'description_sale': product_data.get('short_description'),
                }
                
                # Image Sync
                images = product_data.get('images', [])
                if images:
                    try:
                        img_url = images[0].get('src')
                        img_res = requests.get(img_url, timeout=10)
                        if img_res.status_code == 200:
                            template_vals['image_1920'] = base64.b64encode(img_res.content)
                    except Exception as e:
                        _logger.error("Failed to download image: %s" % str(e))
                
                # Map Categories
                cat_ids = product_data.get('categories', [])
                if cat_ids:
                    cat_mapping = self.env['woo.product.category.mapping'].search([
                        ('backend_id', '=', self.backend_id.id),
                        ('woo_id', '=', str(cat_ids[0].get('id')))
                    ], limit=1)
                    if cat_mapping:
                        template_vals['categ_id'] = cat_mapping.odoo_id.id

                # 3. Handle Variable Products (Attributes & Variants)
                if type == 'variable':
                    # Process Attributes
                    attr_line_vals = []
                    for attr_data in product_data.get('attributes', []):
                        # Find Attribute Mapping
                        attr_mapping = self.env['woo.product.attribute.mapping'].search([
                            ('backend_id', '=', self.backend_id.id),
                            ('woo_id', '=', str(attr_data.get('id')))
                        ], limit=1)
                        
                        if attr_mapping:
                            # Process Attribute Values
                            value_ids = []
                            for val_name in attr_data.get('options', []):
                                # Get or Create Attribute Value
                                value = self.env['product.attribute.value'].search([
                                    ('attribute_id', '=', attr_mapping.odoo_id.id),
                                    ('name', '=', val_name)
                                ], limit=1)
                                if not value:
                                    value = self.env['product.attribute.value'].create({
                                        'name': val_name,
                                        'attribute_id': attr_mapping.odoo_id.id
                                    })
                                value_ids.append(value.id)
                            
                            if value_ids:
                                attr_line_vals.append((0, 0, {
                                    'attribute_id': attr_mapping.odoo_id.id,
                                    'value_ids': [(6, 0, value_ids)]
                                }))
                    
                    if attr_line_vals:
                        template_vals['attribute_line_ids'] = attr_line_vals

                # 4. Create Odoo Template
                odoo_template = self.env['product.template'].create(template_vals)
                
                # Create Template Mapping
                self.env['woo.product.template.mapping'].create({
                    'backend_id': self.backend_id.id,
                    'woo_id': woo_id,
                    'odoo_id': odoo_template.id
                })
                
                # 5. Handle Variations for Variable Products
                if type == 'variable':
                    self._import_variations(odoo_template, woo_id, wcapi)
                
                total_imported += 1
            
            page += 1
            
        return self._notification(_("Imported %d new products.") % total_imported)

    def _import_variations(self, odoo_template, woo_template_id, wcapi):
        """Import variations for a variable product."""
        response = wcapi.get("products/%s/variations" % woo_template_id)
        if response.status_code != 200:
            return
            
        variations = response.json()
        for var_data in variations:
            woo_var_id = str(var_data.get('id'))
            sku = var_data.get('sku')
            
            # Find matching Odoo variant based on attributes
            # (Simplified: Odoo auto-creates variants, we just need to map them)
            # In a real connector, we match by attribute values
            # For now, let's just find by SKU if available, or just map sequentially
            # A more robust way is to match by attribute value IDs
            
            # Let's try to find variant by SKU or just map to one of the template variants
            odoo_variant = odoo_template.product_variant_ids.filtered(lambda p: p.default_code == sku)
            if not odoo_variant:
                # Fallback: find by attribute matching (Complex, skipping for basic version)
                # For this basic Pro version, we'll map the first unmapped variant
                mapped_variant_ids = self.env['woo.product.product.mapping'].search([
                    ('backend_id', '=', self.backend_id.id)
                ]).mapped('odoo_id').ids
                odoo_variant = odoo_template.product_variant_ids.filtered(lambda p: p.id not in mapped_variant_ids)[:1]
            
            if odoo_variant:
                if sku:
                    odoo_variant.default_code = sku
                
                self.env['woo.product.product.mapping'].create({
                    'backend_id': self.backend_id.id,
                    'woo_id': woo_var_id,
                    'odoo_id': odoo_variant.id
                })

    def _import_orders(self):
        """Import orders from WooCommerce."""
        wcapi = self.backend_id.get_woo_api()
        response = wcapi.get("orders", params={"status": "processing", "per_page": 50})
        if response.status_code != 200:
            raise UserError(_("Failed to fetch orders: %s") % response.text)
            
        orders_data = response.json()
        total_imported = 0
        
        for order in orders_data:
            woo_id = str(order.get('id'))
            existing = self.env['sale.order'].search([
                ('woo_order_id', '=', woo_id),
                ('woo_backend_id', '=', self.backend_id.id)
            ], limit=1)
            if existing:
                continue
                
            billing = order.get('billing', {})
            email = billing.get('email')
            partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': "%s %s" % (billing.get('first_name'), billing.get('last_name')),
                    'email': email,
                    'phone': billing.get('phone'),
                    'customer_rank': 1,
                })
            
            order_vals = {
                'partner_id': partner.id,
                'woo_order_id': woo_id,
                'woo_backend_id': self.backend_id.id,
                'warehouse_id': self.backend_id.warehouse_id.id,
                'pricelist_id': self.backend_id.pricelist_id.id,
                'order_line': []
            }
            
            for line in order.get('line_items', []):
                woo_prod_id = str(line.get('product_id'))
                woo_var_id = str(line.get('variation_id'))
                qty = line.get('quantity')
                price = line.get('price')
                
                mapping = False
                if woo_var_id and woo_var_id != '0':
                    mapping = self.env['woo.product.product.mapping'].search([
                        ('backend_id', '=', self.backend_id.id),
                        ('woo_id', '=', woo_var_id)
                    ], limit=1)
                else:
                    template_mapping = self.env['woo.product.template.mapping'].search([
                        ('backend_id', '=', self.backend_id.id),
                        ('woo_id', '=', woo_prod_id)
                    ], limit=1)
                    if template_mapping:
                        mapping = template_mapping.odoo_id.product_variant_ids[:1]
                
                if mapping:
                    product = mapping.odoo_id if hasattr(mapping, 'odoo_id') else mapping
                    order_vals['order_line'].append((0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': qty,
                        'price_unit': price,
                    }))
            
            if order_vals['order_line']:
                self.env['sale.order'].create(order_vals)
                total_imported += 1
                
        return self._notification(_("Imported %d new orders.") % total_imported)

    def _export_stock(self):
        """Export stock levels from Odoo to WooCommerce."""
        wcapi = self.backend_id.get_woo_api()
        warehouse = self.backend_id.warehouse_id
        mappings = self.env['woo.product.product.mapping'].search([
            ('backend_id', '=', self.backend_id.id)
        ])
        
        total_updated = 0
        batch_data = []
        for mapping in mappings:
            product = mapping.odoo_id
            qty = product.with_context(warehouse=warehouse.id).qty_available
            batch_data.append({
                'id': int(mapping.woo_id),
                'manage_stock': True,
                'stock_quantity': int(qty)
            })
            if len(batch_data) >= 50:
                wcapi.post("products/batch", {'update': batch_data})
                batch_data = []
            total_updated += 1
            
        if batch_data:
            wcapi.post("products/batch", {'update': batch_data})
            
        return self._notification(_("Updated stock for %d products.") % total_updated)

    def _export_products(self):
        """Export selected products from Odoo to WooCommerce."""
        wcapi = self.backend_id.get_woo_api()
        products = self.env['product.template'].search([('sale_ok', '=', True)], limit=50)
        total_exported = 0
        
        for product in products:
            mapping = self.env['woo.product.template.mapping'].search([
                ('backend_id', '=', self.backend_id.id),
                ('odoo_id', '=', product.id)
            ], limit=1)
            
            data = {
                'name': product.name,
                'type': 'simple',
                'regular_price': str(product.list_price),
                'sku': product.default_code or '',
            }
            
            if mapping:
                wcapi.put("products/%s" % mapping.woo_id, data)
            else:
                response = wcapi.post("products", data)
                if response.status_code == 201:
                    new_data = response.json()
                    self.env['woo.product.template.mapping'].create({
                        'backend_id': self.backend_id.id,
                        'woo_id': str(new_data.get('id')),
                        'odoo_id': product.id
                    })
            total_exported += 1
            
        return self._notification(_("Exported/Updated %d products.") % total_exported)

    def _notification(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Operation Complete'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }
