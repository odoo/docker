import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { PrintRecMessage } from "@l10n_it_pos/app/fiscal_printer/commands";
import { Font } from "@l10n_it_pos/app/fiscal_printer/commands/types";
import { Heading } from "@l10n_it_pos/app/documents/entities";

export class Header extends Component {
    static template = "l10n_it_pos.FiscalDocumentHeader";

    static components = {
        PrintRecMessage,
    };

    setup() {
        this.pos = usePos();
        this.order = this.pos.get_order();
    }

    get headers() {
        Heading.resetIndex();
        const company = this.pos.company;
        const cashier = this.pos.get_cashier();

        const headings = [
            new Heading(company.partner_id.name, Font.DOUBLE_HEIGHT),
            company.phone && new Heading(`Tel: ${company.phone}`),
            company.vat && new Heading(`${company.country_id?.vat_label || "IVA"}: ${company.vat}`),
            company.email && new Heading(company.email),
            company.website && new Heading(company.website),
            company.partner_id.contact_address &&
                new Heading(company.partner_id.contact_address.replace(/\n/g, " ")),
            this.pos.config.header && new Heading(this.pos.config.header),
            cashier?.name && new Heading(_t("Served by %s", cashier.name), Font.BOLD),
        ];

        return headings.filter(Boolean);
    }
}
