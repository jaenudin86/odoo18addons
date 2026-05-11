/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

// Kita patch PosStore saja, karena ini adalah jantung POS yang pasti ada
patch(PosStore.prototype, {
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }

        // Validasi SN jika kodenya panjang
        if (code && code.length > 5) {
            const lots = this.models['stock.lot'].filter((l) => l.name === code);
            const product = this.models['product.product'].filter((p) => p.barcode === code);
            
            if (lots.length === 0 && product.length === 0) {
                window.alert(_t(`Kode '${code}' tidak dikenal sebagai Produk atau Serial Number yang sah!`));
                return false;
            }
        }
        return super.scan_barcode(code);
    },

    // Validasi saat input manual di pop-up
    async addLotToOrderline(line, lotNames) {
        for (const lotName of lotNames) {
            const lots = this.models['stock.lot'].filter((l) => l.name === lotName.trim());
            if (lots.length === 0) {
                window.alert(_t(`Serial Number '${lotName}' tidak ditemukan di sistem!`));
                return false;
            }
        }
        return super.addLotToOrderline(...arguments);
    }
});
