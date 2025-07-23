import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

/**
 * Patches the PosOrderline model to include additional display data.
*/
patch(PosOrderline.prototype, {
    /**
     * Extends the original getDisplayData method to include the product ID.
     *
     * @returns {Object} The display data for the POS order line, including the product ID.
     */
    getDisplayData() {
        return {
            ...super.getDisplayData(),
             product_id: this.get_product().id,
        }
    }
});
