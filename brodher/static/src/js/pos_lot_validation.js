/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED V2");

// Beri nama pada patch agar Odoo 18 lebih mantap menimpanya
patch(PosStore.prototype, {
    async addProductToCurrentOrder(product, options) {
        // TEST: Jika ini tidak muncul saat klik produk, berarti patch gagal
        console.log("DEBUG: addProductToCurrentOrder dipanggil untuk", product.display_name);
        
        const result = await super.addProductToCurrentOrder(...arguments);
        
        // Cek SN setelah produk masuk
        const order = this.get_order();
        if (order) {
            const lastLine = order.get_last_orderline();
            if (lastLine && lastLine.product_id.tracking === 'serial') {
                this._validateOrderlineLots(lastLine);
            }
        }
        return result;
    },

    async editPackLotLines(line) {
        // TEST: Jika ini tidak muncul saat klik tombol SN di keranjang
        console.log("DEBUG: editPackLotLines dipanggil");
        
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            this._validateOrderlineLots(line);
        }
        return result;
    },

    _validateOrderlineLots(line) {
        const lotLines = line.pack_lot_lines || [];
        const lotNames = lotLines.map(l => l.lot_name);
        
        console.log("DEBUG: Validating Lots:", lotNames);
        
        for (const lotName of lotNames) {
            if (lotName) {
                // Gunakan pencarian di model stock.lot
                const foundLot = this.models['stock.lot']?.find(l => l.name === lotName.trim());
                
                if (!foundLot) {
                    window.alert(_t(`Serial Number '${lotName}' TIDAK SAH! Mohon gunakan QR Code.`));
                    line.pack_lot_lines = [];
                    // Paksa buka kembali pop-up SN
                    this.editPackLotLines(line);
                    return false;
                }
            }
        }
        return true;
    }
});
