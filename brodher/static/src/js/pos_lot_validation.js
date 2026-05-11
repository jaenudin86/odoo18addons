/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED");

patch(PosStore.prototype, {
    // Kita jaga di fungsi paling dasar untuk memproses barcode/SN
    async _processData(data) {
        const result = await super._processData(...arguments);
        console.log("[Brodher POS] _processData triggered", data);
        return result;
    },

    // Jaga saat SN dimasukkan ke baris pesanan
    async editPackLotLines(line) {
        // ALERT DEBUG: Untuk tahu apakah fungsi ini dipanggil
        window.alert("Sedang memproses Serial Number...");
        
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            const lotLines = line.pack_lot_lines || [];
            const allLots = this.models['stock.lot'] || [];
            
            for (const lotLine of lotLines) {
                const name = (lotLine.lot_name || "").trim();
                if (name) {
                    const found = allLots.find(l => l.name === name);
                    if (!found) {
                        window.alert(_t(`SN '${name}' TIDAK VALID! Mohon gunakan QR Code yang sah.`));
                        line.pack_lot_lines = []; // Kosongkan
                        return this.editPackLotLines(line); // Paksa buka lagi
                    }
                }
            }
        }
        return result;
    }
});
