/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED");

patch(PosStore.prototype, {
    // Fungsi ini dipanggil saat pop-up SN ditutup di Odoo 18
    async editPackLotLines(line) {
        const result = await super.editPackLotLines(...arguments);
        
        // Jika user klik OK (result !== null/false)
        if (result) {
            const lotLines = line.pack_lot_lines || [];
            console.log("[Brodher POS] Validating Lot Lines in PosStore:", lotLines);
            
            for (const lotLine of lotLines) {
                const lotName = (lotLine.lot_name || "").trim();
                if (lotName) {
                    // Cari lot di database lokal POS Odoo 18
                    const lots = this.models['stock.lot'].filter((l) => l.name === lotName);
                    
                    if (lots.length === 0) {
                        window.alert(_t(`Serial Number '${lotName}' tidak ditemukan di sistem! Anda tidak bisa memasukkan nomor asal.`));
                        
                        // Kosongkan SN agar tidak bisa lanjut bayar
                        line.pack_lot_lines = [];
                        
                        // Buka kembali pop-up nya agar user dipaksa input yang benar
                        return this.editPackLotLines(line);
                    }
                }
            }
        }
        return result;
    },

    // Validasi saat SCAN
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }
        if (code && code.length > 5) {
            const lots = this.models['stock.lot'].filter((l) => l.name === code);
            const product = this.models['product.product'].filter((p) => p.barcode === code);
            
            if (lots.length === 0 && product.length === 0) {
                window.alert(_t(`Kode '${code}' tidak dikenal sebagai Produk atau Serial Number yang sah!`));
                return false;
            }
        }
        return super.scan_barcode(code);
    }
});
