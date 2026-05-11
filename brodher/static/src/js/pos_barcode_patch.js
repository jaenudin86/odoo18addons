/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/barcode_reader_service";
import { _t } from "@web/core/l10n/translation";

patch(BarcodeReader.prototype, {
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }

        // Cek apakah ini SN (biasanya panjang)
        if (code && code.length > 5) {
            const lots = this.pos.models['stock.lot'].filter((l) => l.name === code);
            const product = this.pos.models['product.product'].filter((p) => p.barcode === code);
            
            // Jika bukan produk dan bukan lot terdaftar
            if (lots.length === 0 && product.length === 0) {
                window.alert(_t(`Kode '${code}' tidak dikenal sebagai Produk atau Serial Number yang sah!`));
                return;
            }
        }

        return super.scan_barcode(code);
    },
});
