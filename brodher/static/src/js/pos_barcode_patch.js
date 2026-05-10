/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/barcode_reader_service";

patch(BarcodeReader.prototype, {
    /**
     * Override scan_barcode to handle concatenated strings separated by #
     * Format: SN#ArtNo#Name#Brand#Type#Size
     */
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            // Ambil bagian pertama saja (Serial Number / Barcode Produk)
            const originalCode = code;
            code = parts[0];
            console.log(`[Brodher POS] Barcode gabungan terdeteksi: "${originalCode}". Menggunakan: "${code}"`);
        }
        return super.scan_barcode(code);
    },
});
