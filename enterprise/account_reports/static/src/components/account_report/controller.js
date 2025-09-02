/* global owl:readonly */

import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";

import { removeTaxGroupingFromLineId } from "@account_reports/js/util";

export class AccountReportController {
    constructor(action) {
        this.action = action;
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    async load(env) {
        this.env = env;
        this.reportOptionsMap = {};
        this.reportInformationMap = {};
        this.lastOpenedSectionByReport = {};
        this.loadingCallNumberByCacheKey = new Proxy(
            {},
            {
                get(target, name) {
                    return name in target ? target[name] : 0;
                },
                set(target, name, newValue) {
                    target[name] = newValue;
                    return true;
                },
            }
        );
        this.actionReportId = this.action.context.report_id;
        const isOpeningReport = !this.action?.keep_journal_groups_options  // true when opening the report, except when coming from the breadcrumb
        const mainReportOptions = await this.loadReportOptions(this.actionReportId, false, this.action.params?.ignore_session, isOpeningReport);
        const cacheKey = this.getCacheKey(mainReportOptions['sections_source_id'], mainReportOptions['report_id']);

        // We need the options to be set and saved in order for the loading to work properly
        this.options = mainReportOptions;
        this.reportOptionsMap[cacheKey] = mainReportOptions;
        this.incrementCallNumber(cacheKey);
        this.options["loading_call_number"] = this.loadingCallNumberByCacheKey[cacheKey];
        this.saveSessionOptions(mainReportOptions);

        const activeSectionPromise = this.displayReport(mainReportOptions['report_id']);
        this.preLoadClosedSections();
        await activeSectionPromise;
    }

    getCacheKey(sectionsSourceId, reportId) {
        return `${sectionsSourceId}_${reportId}`
    }

    incrementCallNumber(cacheKey = null) {
        if (!cacheKey) {
            cacheKey = this.getCacheKey(this.options['sections_source_id'], this.options['report_id']);
        }
        this.loadingCallNumberByCacheKey[cacheKey] += 1;
    }

    async displayReport(reportId) {
        const cacheKey = await this.loadReport(reportId);
        const options = await this.reportOptionsMap[cacheKey];
        const informationMap = await this.reportInformationMap[cacheKey];
        if (
            options !== undefined
            && this.loadingCallNumberByCacheKey[cacheKey] === options["loading_call_number"]
            && (this.lastOpenedSectionByReport === {} || this.lastOpenedSectionByReport[options['selected_variant_id']] === options['selected_section_id'])
        ) {
            // the options gotten from the python correspond to the ones that called this displayReport
            this.options = options;

            // informationMap might be undefined if the promise has been deleted by another call.
            // Don't need to set data, the call that deleted it is coming to re-put data
            if (informationMap !== undefined) {
                this.data = informationMap;
                // If there is a specific order for lines in the options, we want to use it by default
                if (this.areLinesOrdered()) {
                    await this.sortLines();
                }
                this.setLineVisibility(this.lines);
                this.refreshVisibleAnnotations();
                this.saveSessionOptions(this.options);
            }

        }
    }

    async reload(optionPath, newOptions) {
        const rootOptionKey = optionPath ? optionPath.split(".")[0] : "";

        /*
        When reloading the UI after setting an option filter, invalidate the cached options and data of all sections supporting this filter.
        This way, those sections will be reloaded (either synchronously when the user tries to access them or asynchronously via the preloading
        feature), and will then use the new filter value. This ensures the filters are always applied consistently to all sections.
        */
        for (const [cacheKey, cachedOptionsPromise] of Object.entries(this.reportOptionsMap)) {
            let cachedOptions = await cachedOptionsPromise;

            if (rootOptionKey === "" || cachedOptions.hasOwnProperty(rootOptionKey)) {
                delete this.reportOptionsMap[cacheKey];
                delete this.reportInformationMap[cacheKey];
            }
        }

        this.saveSessionOptions(newOptions); // The new options will be loaded from the session. Saving them now ensures the new filter is taken into account.
        await this.displayReport(newOptions['report_id']);
    }

    async preLoadClosedSections() {
        let sectionLoaded = false;
        for (const section of this.options['sections']) {
            // Preload the first non-loaded section we find amongst this report's sections.
            const cacheKey = this.getCacheKey(this.options['sections_source_id'], section.id);
            if (section.id != this.options['report_id'] && !this.reportInformationMap[cacheKey]) {
                await this.loadReport(section.id, true);

                sectionLoaded = true;
                // Stop iterating and schedule next call. We don't go on in the loop in case the cache is reset and we need to restart preloading.
                break;
            }
        }

        let nextCallDelay = (sectionLoaded) ? 100 : 1000;

        const self = this;
        setTimeout(() => self.preLoadClosedSections(), nextCallDelay);
    }

    async loadReport(reportId, preloading=false) {
        const options = await this.loadReportOptions(reportId, preloading, false); // This also sets the promise in the cache
        const reportToDisplayId = options['report_id']; // Might be different from reportId, in case the report to open uses sections

        const cacheKey = this.getCacheKey(options['sections_source_id'], reportToDisplayId)
        if (!this.reportInformationMap[cacheKey]) {
            this.reportInformationMap[cacheKey] = this.orm.call(
                "account.report",
                options.readonly_query ? "get_report_information_readonly" : "get_report_information",
                [
                    reportToDisplayId,
                    options,
                ],
                {
                    context: this.action.context,
                },
            );
        }

        await this.reportInformationMap[cacheKey];

        if (!preloading) {
            if (options['sections'].length)
                this.lastOpenedSectionByReport[options['sections_source_id']] = options['selected_section_id'];
        }

        return cacheKey;
    }

    async loadReportOptions(reportId, preloading=false, ignore_session=false, isOpeningReport=false) {
        const loadOptions = (ignore_session || !this.hasSessionOptions()) ? (this.action.params?.options || {}) : this.sessionOptions();
        const cacheKey = this.getCacheKey(loadOptions['sections_source_id'] || reportId, reportId);

        if (!(cacheKey in this.loadingCallNumberByCacheKey)) {
            this.incrementCallNumber(cacheKey);
        }
        loadOptions["loading_call_number"] = this.loadingCallNumberByCacheKey[cacheKey];

        loadOptions["is_opening_report"] = isOpeningReport;

        if (!this.reportOptionsMap[cacheKey]) {
            // The options for this section are not loaded nor loading. Let's load them !

            if (preloading)
                loadOptions['selected_section_id'] = reportId;
            else {
                /* Reopen the last opened section by default (cannot be done through regular caching, because composite reports' options are not
                cached (since they always reroute). */
                if (this.lastOpenedSectionByReport[reportId])
                    loadOptions['selected_section_id'] = this.lastOpenedSectionByReport[reportId];
            }

            this.reportOptionsMap[cacheKey] = this.orm.call(
                "account.report",
                "get_options",
                [
                   reportId,
                   loadOptions,
                ],
                {
                   context: this.action.context,
                },
            );

            // Wait for the result, and check the report hasn't been rerouted to a section or variant; fix the cache if it has
            let reportOptions = await this.reportOptionsMap[cacheKey];

            // In case of a reroute, also set the cached options into the reroute target's key
            const loadedOptionsCacheKey = this.getCacheKey(reportOptions['sections_source_id'], reportOptions['report_id']);
            if (loadedOptionsCacheKey !== cacheKey) {
                /* We delete the rerouting report from the cache, to avoid redoing this reroute when reloading the cached options, as it would mean
                route reports can never be opened directly if they open some variant by default.*/
                delete this.reportOptionsMap[cacheKey];
                this.reportOptionsMap[loadedOptionsCacheKey] = reportOptions;

                this.loadingCallNumberByCacheKey[loadedOptionsCacheKey] = 1;
                delete this.loadingCallNumberByCacheKey[cacheKey];
                return reportOptions;
            }
        }

        return this.reportOptionsMap[cacheKey];
    }

    //------------------------------------------------------------------------------------------------------------------
    // Generic data getters
    //------------------------------------------------------------------------------------------------------------------
    get buttons() {
        return this.options.buttons;
    }

    get caretOptions() {
        return this.data.caret_options;
    }

    get columnHeadersRenderData() {
        return this.data.column_headers_render_data;
    }

    get columnGroupsTotals() {
        return this.data.column_groups_totals;
    }

    get context() {
        return this.data.context;
    }

    get filters() {
        return this.data.filters;
    }

    get annotations() {
        return this.data.annotations;
    }

    get groups() {
        return this.data.groups;
    }

    get lines() {
        return this.data.lines;
    }

    get warnings() {
        return this.data.warnings;
    }

    get linesOrder() {
        return this.data.lines_order;
    }

    get report() {
        return this.data.report;
    }

    get visibleAnnotations() {
        return this.data.visible_annotations;
    }

    //------------------------------------------------------------------------------------------------------------------
    // Generic data setters
    //------------------------------------------------------------------------------------------------------------------
    set annotations(value) {
        this.data.annotations = value;
    }

    set columnGroupsTotals(value) {
        this.data.column_groups_totals = value;
    }

    set lines(value) {
        this.data.lines = value;
        this.setLineVisibility(this.lines);
    }

    set linesOrder(value) {
        this.data.lines_order = value;
    }

    set visibleAnnotations(value) {
        this.data.visible_annotations = value;
    }

    //------------------------------------------------------------------------------------------------------------------
    // Helpers
    //------------------------------------------------------------------------------------------------------------------
    get needsColumnPercentComparison() {
        return this.options.column_percent_comparison === "growth";
    }

    get hasCustomSubheaders() {
        return this.columnHeadersRenderData.custom_subheaders.length > 0;
    }

    get hasDebugColumn() {
        return Boolean(this.options.show_debug_column);
    }

    get hasStringDate() {
        return "date" in this.options && "string" in this.options.date;
    }

    get hasVisibleAnnotations() {
        return Boolean(this.visibleAnnotations.length);
    }

    get hasBudgetColumn() {
        return this.options.column_headers.some((columns) => {
            return columns.some((column) => {
                return Boolean(column.forced_options?.compute_budget);
            });
        });
    }

    //------------------------------------------------------------------------------------------------------------------
    // Options
    //------------------------------------------------------------------------------------------------------------------
    async _updateOption(operationType, optionPath, optionValue=null, reloadUI=false) {
        const optionKeys = optionPath.split(".");

        let currentOptionKey = null;
        let option = this.options;

        while (optionKeys.length > 1) {
            currentOptionKey = optionKeys.shift();
            option = option[currentOptionKey];

            if (option === undefined)
                throw new Error(`Invalid option key in _updateOption(): ${ currentOptionKey } (${ optionPath })`);
        }

        switch (operationType) {
            case "update":
                option[optionKeys[0]] = optionValue;
                break;
            case "delete":
                delete option[optionKeys[0]];
                break;
            case "toggle":
                option[optionKeys[0]] = !option[optionKeys[0]];
                break;
            default:
                throw new Error(`Invalid operation type in _updateOption(): ${ operationType }`);
        }

        if (reloadUI) {
            this.incrementCallNumber();
            await this.reload(optionPath, this.options);
        }
    }

    async updateOption(optionPath, optionValue, reloadUI=false) {
        await this._updateOption('update', optionPath, optionValue, reloadUI);
    }

    async deleteOption(optionPath, reloadUI=false) {
        await this._updateOption('delete', optionPath, null, reloadUI);
    }

    async toggleOption(optionPath, reloadUI=false) {
        await this._updateOption('toggle', optionPath, null, reloadUI);
    }

    async switchToSection(reportId) {
        this.saveSessionOptions({...this.options, 'selected_section_id': reportId});
        this.displayReport(reportId);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Session options
    //------------------------------------------------------------------------------------------------------------------
    sessionOptionsID() {
        /* Options are stored by action report (so, the report that was targetted by the original action triggering this flow).
        This allows a more intelligent reloading of the previous options during user navigation (especially concerning sections and variants;
        you expect your report to open by default the same section as last time you opened it in this http session).
        */
        return `account.report:${ this.actionReportId }:${ session.user_companies.current_company }`;
    }

    hasSessionOptions() {
        return Boolean(browser.sessionStorage.getItem(this.sessionOptionsID()))
    }

    saveSessionOptions(options) {
        browser.sessionStorage.setItem(this.sessionOptionsID(), JSON.stringify(options));
    }

    sessionOptions() {
        return JSON.parse(browser.sessionStorage.getItem(this.sessionOptionsID()));
    }

    //------------------------------------------------------------------------------------------------------------------
    // Lines
    //------------------------------------------------------------------------------------------------------------------
    lineHasDebugData(lineIndex) {
        return 'debug_popup_data' in this.lines[lineIndex];
    }

    lineHasGrowthComparisonData(lineIndex) {
        return Boolean(this.lines[lineIndex].column_percent_comparison_data);
    }

    isLineAncestorOf(ancestorLineId, lineId) {
        return lineId.startsWith(`${ancestorLineId}|`);
    }

    isLineChildOf(childLineId, lineId) {
        return childLineId.startsWith(`${lineId}|`);
    }

    isLineRelatedTo(relatedLineId, lineId) {
        return this.isLineAncestorOf(relatedLineId, lineId) || this.isLineChildOf(relatedLineId, lineId);
    }

    isNextLineChild(index, lineId) {
        return index < this.lines.length && this.lines[index].id.startsWith(lineId);
    }

    isNextLineDirectChild(index, lineId) {
        return index < this.lines.length && this.lines[index].parent_id === lineId;
    }

    isTotalLine(lineIndex) {
        return this.lines[lineIndex].id.includes("|total~~");
    }

    isLoadMoreLine(lineIndex) {
        return this.lines[lineIndex].id.includes("|load_more~~");
    }

    isLoadedLine(lineIndex) {
        const lineID = this.lines[lineIndex].id;
        const nextLineIndex = lineIndex + 1;

        return this.isNextLineChild(nextLineIndex, lineID) && !this.isTotalLine(nextLineIndex) && !this.isLoadMoreLine(nextLineIndex);
    }

    async replaceLineWith(replaceIndex, newLines) {
        await this.insertLines(replaceIndex, 1, newLines);
    }

    async insertLinesAfter(insertIndex, newLines) {
        await this.insertLines(insertIndex + 1, 0, newLines);
    }

    async insertLines(lineIndex, deleteCount, newLines) {
        this.lines.splice(lineIndex, deleteCount, ...newLines);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Unfolded/Folded lines
    //------------------------------------------------------------------------------------------------------------------
    async unfoldLoadedLine(lineIndex) {
        const lineId = this.lines[lineIndex].id;
        let nextLineIndex = lineIndex + 1;

        while (this.isNextLineChild(nextLineIndex, lineId)) {
            if (this.isNextLineDirectChild(nextLineIndex, lineId)) {
                const nextLine = this.lines[nextLineIndex];
                nextLine.visible = true;
                if (!nextLine.unfoldable && this.isNextLineChild(nextLineIndex + 1, nextLine.id)) {
                    await this.unfoldLine(nextLineIndex);
                }
            }
            nextLineIndex += 1;
        }
        return nextLineIndex;
    }

    async unfoldNewLine(lineIndex) {
        const options = await this.options;
        const newLines = await this.orm.call(
            "account.report",
            options.readonly_query ? "get_expanded_lines_readonly" : "get_expanded_lines",
            [
                this.options['report_id'],
                this.options,
                this.lines[lineIndex].id,
                this.lines[lineIndex].groupby,
                this.lines[lineIndex].expand_function,
                this.lines[lineIndex].progress,
                0,
                this.lines[lineIndex].horizontal_split_side,
            ],
        );

        if (this.areLinesOrdered()) {
            this.updateLinesOrderIndexes(lineIndex, newLines, false)
        }
        this.insertLinesAfter(lineIndex, newLines);

        const totalIndex = lineIndex + newLines.length + 1;

        if (this.filters.show_totals && this.lines[totalIndex] && this.isTotalLine(totalIndex))
            this.lines[totalIndex].visible = true;
        return totalIndex
    }

    /**
     * When unfolding a line of a sorted report, we need to update the linesOrder array by adding the new lines,
     * which will require subsequent updates on the array.
     *
     * - lineOrderValue represents the line index before sorting the report.
     * @param {Integer} lineIndex: Index of the current line
     * @param {Array} newLines: Array of lines to be added
     * @param {Boolean} replaceLine: Useful for the splice of the linesOrder array in case we want to replace some line
     *                               example: With the load more, we want to replace the line with others
     **/
    updateLinesOrderIndexes(lineIndex, newLines, replaceLine) {
        let unfoldedLineIndex;
        // The offset is useful because in case we use 'replaceLineWith' we want to replace the line at index
        // unfoldedLineIndex with the new lines.
        const offset = replaceLine ? 0 : 1;
        for (const [lineOrderIndex, lineOrderValue] of Object.entries(this.linesOrder)) {
            // Since we will have to add new lines into the linesOrder array, we have to update the index of the lines
            // having a bigger index than the one we will unfold.
            // deleteCount of 1 means that a line need to be replaced so the index need to be increase by 1 less than usual
            if (lineOrderValue > lineIndex) {
                this.linesOrder[lineOrderIndex] += newLines.length - replaceLine;
            }
            // The unfolded line is found, providing a reference for adding children in the 'linesOrder' array.
            if (lineOrderValue === lineIndex) {
                unfoldedLineIndex = parseInt(lineOrderIndex)
            }
        }

        const arrayOfNewIndex = Array.from({ length: newLines.length }, (dummy, index) => this.linesOrder[unfoldedLineIndex] + index + offset);
        this.linesOrder.splice(unfoldedLineIndex + offset, replaceLine, ...arrayOfNewIndex);
    }

    async unfoldLine(lineIndex) {
        const targetLine = this.lines[lineIndex];
        let lastLineIndex = lineIndex + 1;

        if (this.isLoadedLine(lineIndex))
            lastLineIndex = await this.unfoldLoadedLine(lineIndex);
        else if (targetLine.expand_function) {
            lastLineIndex = await this.unfoldNewLine(lineIndex);
        }

        this.setLineVisibility(this.lines.slice(lineIndex + 1, lastLineIndex));
        targetLine.unfolded = true;
        this.refreshVisibleAnnotations();

        // Update options
        if (!this.options.unfolded_lines.includes(targetLine.id))
            this.options.unfolded_lines.push(targetLine.id);

        this.saveSessionOptions(this.options);
    }

    foldLine(lineIndex) {
        const targetLine = this.lines[lineIndex];

        let foldedLinesIDs = new Set([targetLine.id]);
        let nextLineIndex = lineIndex + 1;

        while (this.isNextLineChild(nextLineIndex, targetLine.id)) {
            this.lines[nextLineIndex].unfolded = false;
            this.lines[nextLineIndex].visible = false;

            foldedLinesIDs.add(this.lines[nextLineIndex].id);

            nextLineIndex += 1;
        }

        targetLine.unfolded = false;

        this.refreshVisibleAnnotations();

        // Update options
        this.options.unfolded_lines = this.options.unfolded_lines.filter(
            unfoldedLineID => !foldedLinesIDs.has(unfoldedLineID)
        );

        this.saveSessionOptions(this.options);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Ordered lines
    //------------------------------------------------------------------------------------------------------------------
    linesCurrentOrderByColumn(columnIndex) {
        if (this.areLinesOrderedByColumn(columnIndex))
            return this.options.order_column.direction;

        return "default";
    }

    areLinesOrdered() {
        return this.linesOrder != null && this.options.order_column != null;
    }

    areLinesOrderedByColumn(columnIndex) {
        return this.areLinesOrdered() && this.options.order_column.expression_label === this.options.columns[columnIndex].expression_label;
    }

    async sortLinesByColumnAsc(columnIndex) {
        this.options.order_column = {
            expression_label: this.options.columns[columnIndex].expression_label,
            direction: "ASC",
        };

        await this.sortLines();
        this.saveSessionOptions(this.options);
    }

    async sortLinesByColumnDesc(columnIndex) {
        this.options.order_column = {
            expression_label: this.options.columns[columnIndex].expression_label,
            direction: "DESC",
        };

        await this.sortLines();
        this.saveSessionOptions(this.options);
    }

    sortLinesByDefault() {
        delete this.options.order_column;
        delete this.data.lines_order;

        this.saveSessionOptions(this.options);
    }

    async sortLines() {
        this.linesOrder = await this.orm.call(
            "account.report",
            "sort_lines",
            [
                this.lines,
                this.options,
                true,
            ],
            {
                context: this.action.context,
            },
        );
    }

    //------------------------------------------------------------------------------------------------------------------
    // Annotations
    //------------------------------------------------------------------------------------------------------------------
    async refreshAnnotations() {
        this.annotations = await this.orm.call("account.report", "get_annotations", [
            this.action.context.report_id,
            this.options,
        ]);

        this.refreshVisibleAnnotations();
    }

    //------------------------------------------------------------------------------------------------------------------
    // Visibility
    //------------------------------------------------------------------------------------------------------------------

    refreshVisibleAnnotations() {
        const visibleAnnotations = new Proxy(
            {},
            {
                get(target, name) {
                    return name in target ? target[name] : [];
                },
                set(target, name, newValue) {
                    target[name] = newValue;
                    return true;
                },
            }
        );

        this.lines.forEach((line) => {
            line["visible_annotations"] = [];
            const lineWithoutTaxGrouping = removeTaxGroupingFromLineId(line.id);
            if (line.visible && this.annotations[lineWithoutTaxGrouping]) {
                for (const index in this.annotations[lineWithoutTaxGrouping]) {
                    const annotation = this.annotations[lineWithoutTaxGrouping][index];
                    visibleAnnotations[lineWithoutTaxGrouping] = [
                        ...visibleAnnotations[lineWithoutTaxGrouping],
                        { ...annotation },
                    ];
                    line["visible_annotations"].push({
                        ...annotation,
                    });
                }
            }

            if (
                line.visible_annotations &&
                (!this.annotations[lineWithoutTaxGrouping] || !line.visible)
            ) {
                delete line.visible_annotations;
            }
        });

        this.visibleAnnotations = visibleAnnotations;
    }

    /**
        Defines which lines should be visible in the provided list of lines (depending on what is folded).
    **/
    setLineVisibility(linesToAssign) {
        let needHidingChildren = new Set();

        linesToAssign.forEach((line) => {
            line.visible = !needHidingChildren.has(line.parent_id);

            if (!line.visible || (line.unfoldable &! line.unfolded))
                needHidingChildren.add(line.id);
        });

        // If the hide 0 lines is activated we will go through the lines to set the visibility.
        if (this.options.hide_0_lines) {
            this.hideZeroLines(linesToAssign);
        }
    }

    /**
     * Defines whether the line should be visible depending on its value and the ones of its children.
     * For parent lines, it's visible if there is at least one child with a value different from zero
     * or if a child is visible, indicating it's a parent line.
     * For leaf nodes, it's visible if the value is different from zero.
     *
     * By traversing the 'lines' array in reverse, we can set the visibility of the lines easily by keeping
     * a dict of visible lines for each parent.
     *
     * @param {Object} lines - The lines for which we want to determine visibility.
     */
    hideZeroLines(lines) {
        const hasVisibleChildren = new Set();
        const reversed_lines = [...lines].reverse()

        const number_figure_types = ['integer', 'float', 'monetary', 'percentage'];
        reversed_lines.forEach((line) => {
            const isZero = line.columns.every(column => !number_figure_types.includes(column.figure_type) || column.is_zero);

            // If the line has no visible children and all the columns are equals to zero then the line needs to be hidden
            if (!hasVisibleChildren.has(line.id) && isZero) {
                line.visible = false;
            }

            // If the line has a parent_id and is not hidden then we fill the set 'hasVisibleChildren'. Each parent
            // will have an array of his visible children
            if (line.parent_id && line.visible) {
                // This line allows the initialization of that list.
                hasVisibleChildren.add(line.parent_id);
            }
        })
    }

    //------------------------------------------------------------------------------------------------------------------
    // Server calls
    //------------------------------------------------------------------------------------------------------------------
    async reportAction(ev, action, actionParam = null, callOnSectionsSource = false) {
        // 'ev' might be 'undefined' if event is not triggered from a button/anchor
        ev?.preventDefault();
        ev?.stopPropagation();

        let actionOptions = this.options;
        if (callOnSectionsSource) {
            // When calling the sections source, we want to keep track of all unfolded lines of all sections
            const allUnfoldedLines =  this.options.sections.length ? [] : [...this.options['unfolded_lines']]

            for (const sectionData of this.options['sections']) {
                const cacheKey = this.getCacheKey(this.options['sections_source_id'], sectionData['id']);
                const sectionOptions = await this.reportOptionsMap[cacheKey];
                if (sectionOptions)
                    allUnfoldedLines.push(...sectionOptions['unfolded_lines']);
            }

            actionOptions = {...this.options, unfolded_lines: allUnfoldedLines};
        }

        const dispatchReportAction = await this.orm.call(
            "account.report",
            "dispatch_report_action",
            [
                this.options['report_id'],
                actionOptions,
                action,
                actionParam,
                callOnSectionsSource,
            ],
        );
        if (dispatchReportAction?.help) {
            dispatchReportAction.help = owl.markup(dispatchReportAction.help)
        }

        return dispatchReportAction ? this.actionService.doAction(dispatchReportAction) : null;
    }

    // -----------------------------------------------------------------------------------------------------------------
    // Budget
    // -----------------------------------------------------------------------------------------------------------------

    async openBudget(budget) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.report.budget",
            res_id: budget.id,
            views: [[false, "form"]],
        });
    }
}
