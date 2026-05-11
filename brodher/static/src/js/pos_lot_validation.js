/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED");

patch(PosStore.prototype, {
    // JARING A: Saat SN dimasukkan via Barcode atau Pop-up Otomatis
    async selectLotBarcode(line) {
        window.alert("JARING A: selectLotBarcode");
        const result = await super.selectLotBarcode(...arguments);
        if (result) this._validateOrderlineLots(line);
        return result;
    },

    // JARING B: Saat SN ditambahkan ke Orderline
    async addLotToOrderline(line, lotNames) {
        window.alert("JARING B: addLotToOrderline");
        const result = await super.addLotToOrderline(...arguments);
        if (result) this._validateOrderlineLots(line);
        return result;
    },

    // JARING C: Saat klik tombol SN di keranjang
    async editPackLotLines(line) {
        window.alert("JARING C: editPackLotLines");
        const result = await super.editPackLotLines(...arguments);
        if (result) this._validateOrderlineLots(line);
        return result;
    },

    _validateOrderlineLots(line) {
        const lotLines = line.pack_lot_lines || [];
        const lotNames = lotLines.map(l => l.lot_name);
        
        for (const lotName of lotNames) {
            if (lotName) {
                const allLots = this.models['stock.lot'] || [];
                const foundLot = allLots.find(l => l.name === lotName.trim());
                
                if (!foundLot) {
                    window.alert(_t(`Nomor Seri '${lotName}' TIDAK SAH! Silakan scan QR Code yang benar.`));
                    line.pack_lot_lines = [];
                    // Buka kembali pop-up
                    this.editPackLotLines(line);
                    return false;
                }
            }
        }
        return true;
    }
});
