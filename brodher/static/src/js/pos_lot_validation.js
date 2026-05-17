/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

console.log("POS LOT VALIDATION LOADED V6");

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
                const currentOrder = this.pos.get_order();
                if (currentOrder) {
                    const currentLine = currentOrder.get_selected_orderline();
                    if (currentLine) {
                        const product = currentLine.product || (currentLine.get_product ? currentLine.get_product() : null);
                        const productId = product ? product.id : null;
                        const productName = this.props.name || (product ? product.display_name : "");
                        
                        if (productId || productName) {
                            try {
                                for (const lotName of lotNames) {
                                    // Panggil validation di backend secara real-time dengan fallback productName
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
