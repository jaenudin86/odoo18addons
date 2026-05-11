/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

// ALERT TEST: Jika ini muncul, berarti file JS aktif
console.log("POS LOT VALIDATION LOADED");

patch(PosStore.prototype, {
    // Kita cegat di level paling tinggi: saat produk ditambahkan atau di-edit
    async addProductToCurrentOrder(product, options) {
        const result = await super.addProductToCurrentOrder(...arguments);
        // Setelah produk masuk, kita cek apakah ada SN yang terinput (lewat popup otomatis)
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
        const result = await super.editPackLotLines(...arguments);
        if (result) {
            this._validateOrderlineLots(line);
        }
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
                    window.alert(_t(`Serial Number '${lotName}' TIDAK DITEMUKAN! Nomor ini tidak sah.`));
                    // Kosongkan agar tidak bisa bayar
                    line.pack_lot_lines = [];
                    // Paksa buka kembali pop-up nya
                    this.editPackLotLines(line);
                    return false;
                }
            }
        }
        return true;
    },

    // Validasi saat SCAN
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }
        const allLots = this.models['stock.lot'] || [];
        const foundLot = allLots.find(l => l.name === code);
        const foundProduct = this.models['product.product'].find(p => p.barcode === code);
        
        if (code && code.length > 5 && !foundLot && !foundProduct) {
            window.alert(_t(`Kode '${code}' tidak dikenal sebagai Produk atau Serial Number yang sah!`));
            return false;
        }
        return super.scan_barcode(code);
    }
});
