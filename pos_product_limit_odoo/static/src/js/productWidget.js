/** @odoo-module */
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

/**
 * Customizes the behavior of the `productsToDisplay` getter in the ProductScreen.
 * This patch modifies the way products are filtered, sorted, and limited before being displayed
 * based on search input, selected category, and other configurable parameters.**/

patch(ProductScreen.prototype, {
    get productsToDisplay() {
        let list = [];

        if (this.searchWord !== "") {
            list = this.addMainProductsToDisplay(this.getProductsBySearchWord(this.searchWord));
        } else if (this.pos.selectedCategory?.id) {
            list = this.getProductsByCategory(this.pos.selectedCategory);
        } else {
            list = this.products;
        }

        if (!list) {
            return [];
        }

        list = list
            .filter(
                (product) =>
                    ![
                        this.pos.config.tip_product_id?.id,
                        ...this.pos.hiddenProductIds,
                        ...this.pos.session._pos_special_products_ids,
                    ].includes(product.id) && product.available_in_pos
            )
            .slice(0, 100);

        let all_items = this.searchWord !== ""
            ? list
            : list.sort((a, b) => a.display_name.localeCompare(b.display_name));
             // Apply product limit from POS configuration
           let limit_items = all_items
           if (this.env.services.pos.config.product_limit <= 0){
                limit_items = all_items;
            }
            else{
                limit_items = all_items.slice(0,this.env.services.pos.config.product_limit);
            }

            return limit_items;
    }
    });
