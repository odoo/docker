/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { GraphModel } from "@web/views/graph/graph_model";
import { usePlanningModelActions } from "../planning_hooks";


export class PlanningGraphModel extends GraphModel {
    /** @override **/
    setup() {
        super.setup(...arguments);
        this.getHighlightIds = usePlanningModelActions({
            getHighlightPlannedIds: () => this.env.searchModel.highlightPlannedIds,
            getContext: () => this.env.searchModel._context,
        }).getHighlightIds;
    }

    /** @override **/
    async load(searchParams) {
        const highlightIds = await this.getHighlightIds();
        if (highlightIds) {
            searchParams.domain = Domain.and([
                searchParams.domain,
                [["id", "in", highlightIds]]
            ]).toList();
        }
        return await super.load(searchParams);
    }
}
