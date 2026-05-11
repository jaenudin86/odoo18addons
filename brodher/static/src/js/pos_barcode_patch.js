/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/barcode_reader_service";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

patch(BarcodeReader.prototype, {
    /**
     * Override scan_barcode to handle concatenated strings separated by #
     * Format: SN#ArtNo#Name#Brand#Type#Size
     */
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }

        // VALIDASI: Jika kode ini adalah Serial Number, pastikan dia ada di sistem
        // Kita cek apakah ada lot dengan nama tersebut di database lokal POS
        const lots = this.pos.models['stock.lot'].filter((l) => l.name === code);
        
        // Jika kodenya panjang (seperti SN) tapi tidak ditemukan di database Lot
        // Kita bisa asumsikan ini percobaan input SN asal
        if (code.length > 5 && lots.length === 0) {
             const product = this.pos.models['product.product'].filter((p) => p.barcode === code);
             // Kalau bukan barcode produk, berarti ini SN asal
             if (product.length === 0) {
                this.env.services.popup.add(ErrorPopup, {
                    title: _t("Barcode/SN Tidak Valid"),
                    body: _t(`Kode '${code}' tidak terdaftar sebagai Produk atau Serial Number yang sah!`),
                });
                return;
             }
        }

        return super.scan_barcode(code);
    },
});
