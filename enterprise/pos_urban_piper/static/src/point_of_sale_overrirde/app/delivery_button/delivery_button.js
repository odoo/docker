import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class DeliveryButton extends Component {
    static template = "pos_urban_piper.DeliveryButton";
    static components = {
        Dropdown,
        DropdownItem,
    };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }

    goToOrders(deliveryProvider, upState, filter = "ONGOING") {
        const stateOverride = {
            search: {
                fieldName: "DELIVERYPROVIDER",
                searchTerm: deliveryProvider,
            },
            filter: filter,
        };
        if (this.pos.mainScreen.component?.name == "TicketScreen") {
            this.env.services.ui.block();
            this.pos.ticket_screen_mobile_pane = "left";
            this.pos.closeScreen();
            setTimeout(() => {
                this.pos.showScreen("TicketScreen", { stateOverride: stateOverride, upState });
                this.env.services.ui.unblock();
            }, 300);
            return;
        }
        this.pos.showScreen("TicketScreen", { stateOverride: stateOverride, upState });
    }
}
