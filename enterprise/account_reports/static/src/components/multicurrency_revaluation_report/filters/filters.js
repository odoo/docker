import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

export class MulticurrencyRevaluationReportFilters extends AccountReportFilters {
    static template = "account_reports.MulticurrencyRevaluationReportFilters";

    //------------------------------------------------------------------------------------------------------------------
    // Custom filters
    //------------------------------------------------------------------------------------------------------------------
    async filterExchangeRate(ev, currencyId) {
        this.controller.options.currency_rates[currencyId].rate = ev.currentTarget.value;
    }
}

AccountReport.registerCustomComponent(MulticurrencyRevaluationReportFilters);
