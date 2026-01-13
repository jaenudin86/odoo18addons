from odoo import models, api


class ProductQrcodeReport(models.AbstractModel):
    _name = 'report.brodher_product_serial.product_qrcode_label_template'
    _description = 'Product QR Code Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['product.qrcode.label.wizard'].browse(docids)
        
        label_data = []
        for doc in docs:
            for product in doc.product_ids:
                for i in range(doc.quantity):
                    label_data.append({
                        'name': product.display_name or product.name,
                        'barcode': product.barcode or product.default_code or '',
                        'product_id': product.id,
                    })
        
        return {
            'doc_ids': docids,
            'doc_model': 'product.qrcode.label.wizard',
            'docs': docs,
            'label_data': label_data,
        }