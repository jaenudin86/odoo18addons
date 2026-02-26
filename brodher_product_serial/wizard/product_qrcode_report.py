from odoo import models, api

class ProductQrcodeReport(models.AbstractModel):
    _name = 'report.brodher_product_serial.product_qrcode_label_template'
    _description = 'Product QR Code Label Report'

    
    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['product.qrcode.label.wizard'].browse(docids)
        
        label_data = []
        for doc in docs:
            # pakai variant_ids kalau ada, fallback ke product_ids
            products = doc.variant_ids if doc.variant_ids else doc.product_ids
            for product in products:
                for i in range(doc.quantity):
                    variant_values = product.product_template_attribute_value_ids.mapped('name')
                    variant_str = ' / '.join(variant_values) if variant_values else ''
                    
                    label_data.append({
                        'ir_number': product.default_code or '',
                        'name': product.product_tmpl_id.name,
                        'variant': variant_str,
                        'barcode': product.barcode or product.default_code or '',
                        'product_id': product.id,
                    })
        
        return {
            'doc_ids': docids,
            'doc_model': 'product.qrcode.label.wizard',
            'docs': docs,
            'label_data': label_data,
        }