from odoo import models, fields, api
import base64
import io
import qrcode

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_generate_qr_labels(self):
        for move in self.move_lines:
            for i in range(int(move.quantity_done)):
                self.env['qr.label.serial'].create({
                    'product_id': move.product_id.id,
                    'picking_id': self.id,
                })

class QLabelSerial(models.Model):
    _name = 'qr.label.serial'
    _description = 'QR Label Serial'

    name = fields.Char(string="Serial", readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('qr.label.serial'))
    product_id = fields.Many2one('product.product', string="Product", required=True)
    picking_id = fields.Many2one('stock.picking', string="Stock Picking")

    def get_qr_code_base64(self):
        for record in self:
            qr = qrcode.QRCode(box_size=4, border=2)
            qr.add_data(record.name)
            qr.make(fit=True)
            img = qr.make_image()
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_str}"