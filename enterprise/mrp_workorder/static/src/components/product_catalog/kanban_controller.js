/** @odoo-module **/

import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanController.prototype, {
    get canCreate() {
        return !this.props.context.from_shop_floor;  // Hide the "Back to Production" button if we are in the shop floor.
    },
});
