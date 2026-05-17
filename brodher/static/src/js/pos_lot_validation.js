/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Orderline } from "@point_of_sale/app/store/models";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED V8 - WITH QTY BLOCK");

// 1. Patch EditListPopup to perform real-time backend validation on Lot/Serial Numbers manually entered
patch(EditListPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = useService("pos");
        this.orm = useService("orm");
    },

    async confirm() {
        // Cek apakah ini popup Lot/Serial
        const isLotPopup = this.props.title && (
            this.props.title.includes("Serial") || 
            this.props.title.includes("Lot") || 
            this.props.title.includes("Nomor")
        );

        if (isLotPopup) {
            const lotNames = this.state.array.map(item => (item.text || "").trim()).filter(Boolean);
            if (lotNames.length > 0) {
                const productName = this.props.name || "";
                let productId = null;

                // Cari product ID berdasarkan nama produk yang tertera di popup props secara akurat
                if (productName && this.pos) {
                    // Coba cari di local POS models
                    const products = this.pos.models ? this.pos.models["product.product"] : null;
                    if (products && typeof products.find === 'function') {
                        const foundProduct = products.find(p => p.display_name === productName || p.name === productName);
                        if (foundProduct) {
                            productId = foundProduct.id;
                        }
                    }
                    
                    // Fallback: cari di seluruh orderlines di keranjang jika ada yang namanya cocok
                    if (!productId) {
                        const currentOrder = this.pos.get_order();
                        if (currentOrder && typeof currentOrder.get_orderlines === 'function') {
                            const lines = currentOrder.get_orderlines() || [];
                            const matchingLine = lines.find(line => {
                                const p = line.product || (line.get_product ? line.get_product() : null);
                                return p && (p.display_name === productName || p.name === productName);
                            });
                            if (matchingLine) {
                                const p = matchingLine.product || (matchingLine.get_product ? matchingLine.get_product() : null);
                                productId = p ? p.id : null;
                            }
                        }
                    }
                }

                if (productId || productName) {
                    try {
                        for (const lotName of lotNames) {
                            // Panggil validation di backend secara real-time
                            const res = await this.orm.call(
                                "pos.session",
                                "check_lot_validation",
                                [productId, lotName, productName]
                            );
                            
                            if (res && res.status !== 'ok') {
                                // Tampilkan alert error dan batalkan konfirmasi (popup tetap terbuka)
                                window.alert(res.message);
                                return;
                            }
                        }
                    } catch (err) {
                        console.error("Error validating lot:", err);
                    }
                }
            }
        }

        // Jika semua lolos validasi, panggil standard confirm
        return super.confirm(...arguments);
    }
});

// 2. Patch PosStore to handle scanned barcodes
patch(PosStore.prototype, {
    async scan_barcode(code) {
        if (code && code.includes("#")) {
            const parts = code.split("#");
            code = parts[0];
        }
        return super.scan_barcode(code);
    }
});

// 3. Patch Orderline to prevent manual quantity modification for Serial-tracked products
patch(Orderline.prototype, {
    set_quantity(quantity, keep_price) {
        const product = this.product || (this.get_product ? this.get_product() : null);
        
        // Cek jika produk dilacak berdasarkan Serial Number (serial)
        if (product && product.tracking === 'serial') {
            // Izinkan jika ingin menghapus baris (qty 0 atau 'remove')
            if (quantity === 0 || quantity === "remove" || quantity === "") {
                return super.set_quantity(...arguments);
            }
            
            // Cari tahu jumlah Serial Number yang sudah terdaftar di line ini
            const lotCount = this.pack_lot_lines ? this.pack_lot_lines.length : 0;
            const maxQty = lotCount > 0 ? lotCount : 1;
            
            // Blokir jika kasir mencoba menaikkan qty lebih dari jumlah SN yang discan/dimasukkan
            if (parseFloat(quantity) > maxQty) {
                window.alert(_t("Produk ber-Serial Number tidak dapat diubah Qty secara manual! Silakan scan QR Code Serial Number untuk menambah barang."));
                return;
            }
        }
        return super.set_quantity(...arguments);
    }
});
