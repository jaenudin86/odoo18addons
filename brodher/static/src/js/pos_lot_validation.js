/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED V3");
window.alert("VALIDASI AKTIF V3");

patch(PosStore.prototype, {
    // 1. Validasi saat SCAN Barcode
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }
        if (code && code.length > 5) {
            const foundLot = this.models['stock.lot'].find(l => l.name === code);
            const foundProduct = this.models['product.product'].find(p => p.barcode === code);
            
            if (!foundLot && !foundProduct) {
                window.alert(_t(`Kode '${code}' TIDAK SAH! Mohon gunakan QR Code yang terdaftar.`));
                return false;
            }
        }
        return super.scan_barcode(code);
    },

    // 2. Validasi saat klik OK di pop-up mana pun (otomatis atau manual)
    async editPackLotLines(line) {
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            const lotLines = line.pack_lot_lines || [];
            for (const lotLine of lotLines) {
                const lotName = (lotLine.lot_name || "").trim();
                if (lotName) {
                    const foundLot = this.models['stock.lot'].find(l => l.name === lotName);
                    if (!foundLot) {
                        window.alert(_t(`Serial Number '${lotName}' TIDAK DITEMUKAN! Sistem akan menghapusnya.`));
                        line.pack_lot_lines = []; // Kosongkan
                        return this.editPackLotLines(line); // Buka kembali pop-up
                    }
                }
            }
        }
        return result;
    }
});
