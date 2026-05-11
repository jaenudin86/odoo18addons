/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    // 1. Validasi saat SCAN Barcode
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }

        // Jika kodenya mirip SN (panjang > 5)
        if (code && code.length > 5) {
            const allLots = this.models['stock.lot'] || [];
            const foundLot = allLots.find(l => l.name === code);
            const foundProduct = this.models['product.product'].find(p => p.barcode === code);
            
            if (!foundLot && !foundProduct) {
                window.alert(_t(`Kode '${code}' tidak dikenal sebagai Produk atau Serial Number yang sah!`));
                return false;
            }
        }
        return super.scan_barcode(code);
    },

    // 2. Validasi saat INPUT MANUAL di pop-up
    async editPackLotLines(line) {
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            const lotNames = line.pack_lot_lines.map(l => l.lot_name);
            for (const lotName of lotNames) {
                if (lotName) {
                    const allLots = this.models['stock.lot'] || [];
                    const foundLot = allLots.find(l => l.name === lotName.trim());
                    
                    if (!foundLot) {
                        window.alert(_t(`Serial Number '${lotName}' TIDAK DITEMUKAN di sistem! Anda tidak bisa memasukkan nomor asal.`));
                        line.pack_lot_lines = [];
                        return false;
                    }
                }
            }
        }
        return result;
    }
});
