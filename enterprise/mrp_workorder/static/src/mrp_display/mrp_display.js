/** @odoo-module */

import { Layout } from "@web/search/layout";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { Pager } from "@web/core/pager/pager";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useModel } from "@web/model/model";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { ControlPanelButtons } from "@mrp_workorder/mrp_display/control_panel";
import { MrpDisplayRecord } from "@mrp_workorder/mrp_display/mrp_display_record";
import { MrpWorkcenterDialog } from "./dialog/mrp_workcenter_dialog";
import { makeActiveField } from "@web/model/relational_model/utils";
import { MrpDisplayEmployeesPanel } from "@mrp_workorder/mrp_display/employees_panel";
import { PinPopup } from "@mrp_workorder/components/pin_popup";
import { useConnectedEmployee } from "@mrp_workorder/mrp_display/hooks/employee_hooks";
import { MrpDisplaySearchBar } from "@mrp_workorder/mrp_display/search_bar";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Component, onWillDestroy, onWillStart, useState, useSubEnv } from "@odoo/owl";

export class MrpDisplay extends Component {
    static template = "mrp_workorder.MrpDisplay";
    static components = {
        Layout,
        ControlPanelButtons,
        MrpDisplayRecord,
        MrpDisplayEmployeesPanel,
        PinPopup,
        MrpDisplaySearchBar,
        CheckboxItem,
        Pager,
    };
    static props = {
        resModel: String,
        action: { type: Object, optional: true },
        comparison: { validate: () => true },
        models: { type: Object },
        domain: { type: Array },
        display: { type: Object, optional: true },
        context: { type: Object, optional: true },
        groupBy: { type: Array, element: String },
        orderBy: { type: Array, element: Object },
    };

    setup() {
        this.homeMenu = useService("home_menu");
        this.viewService = useService("view");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.pwaService = useService("pwa");

        this.display = {
            ...this.props.display,
        };

        this.validationStack = {
            "mrp.production": [],
            "mrp.workorder": [],
        };
        this.adminId = false;
        this.barcodeTargetRecordId = false;
        if (
            this.props.context.active_model === "stock.picking.type" &&
            this.props.context.active_id
        ) {
            this.pickingTypeId = this.props.context.active_id;
        }
        useSubEnv({
            localStorageName: `mrp_workorder.db_${session.db}.user_${user.userId}.picking_type_${this.pickingTypeId}`,
        });

        const workcenters = JSON.parse(localStorage.getItem(this.env.localStorageName)) || [];
        let activeWorkcenter = this.props.context.workcenter_id || false;
        // If no workcenter by default but some WC were already selected, selects the first one.
        if (!activeWorkcenter && workcenters.length) {
            activeWorkcenter = workcenters[0].id;
        }

        this.state = useState({
            activeResModel: activeWorkcenter ? "mrp.workorder" : this.props.resModel,
            activeWorkcenter,
            workcenters,
            showEmployeesPanel: localStorage.getItem("mrp_workorder.show_employees") === "true",
            canLoadSamples: false,
            offset: 0,
            limit: 40,
        });

        const params = this._makeModelParams();

        this.model = useState(useModel(RelationalModel, params));
        useSubEnv({
            model: this.model,
            reload: async (record = false) => {
                if (record) {
                    while (record && record.resModel !== "mrp.production") {
                        record = record._parentRecord;
                    }
                    await record.load();
                    await record.model.notify();
                } else {
                    clearInterval(this.refreshInterval);
                    await this.model.root.load({
                        offset: this.state.offset,
                        limit: this.state.limit,
                    });
                    this.refreshInterval = setInterval(() => {
                        this.env.reload();
                    }, 600000);
                }
                await this.useEmployee.getConnectedEmployees();
            },
        });
        this.useEmployee = useConnectedEmployee("mrp_display", this.props.context, this.actionService, this.dialogService);
        this.barcode = useService("barcode");
        useBus(this.barcode.bus, "barcode_scanned", (event) =>
            this._onBarcodeScanned(event.detail.barcode)
        );
        this.notification = useService("notification");
        this.orm = useService("orm");
        onWillStart(async () => {
            this.groups = {
                byproducts: await user.hasGroup("mrp.group_mrp_byproducts"),
                uom: await user.hasGroup("uom.group_uom"),
                workorders: await user.hasGroup("mrp.group_mrp_routings"),
                timer: await user.hasGroup("mrp_workorder.group_mrp_wo_tablet_timer")
            };
            this.env.searchModel.workorders = this.groups.workorders;
            this.group_mrp_routings = await user.hasGroup("mrp.group_mrp_routings");
            this.env.searchModel.setWorkcenterFilter(this.state.workcenters);
            await this.useEmployee.getConnectedEmployees(true);
            // select the workcenter received in the context
            if (this.props.context.workcenter_id) {
                const workcenters = await this.orm.searchRead("mrp.workcenter", [["id", "=", this.state.activeWorkcenter]], ["display_name"]);
                this.state.workcenters = workcenters;
            }
            if (
                JSON.parse(localStorage.getItem(this.env.localStorageName)) === null &&
                this.group_mrp_routings
            ) {
                this.toggleWorkcenterDialog(false);
            }
            this.state.canLoadSamples = await this.orm.call("mrp.production", "can_load_samples", [
                [],
            ]);
            this.refreshInterval = setInterval(() => {
                this.env.reload();
            }, 600000);
        });
        onWillDestroy(async () => {
            clearInterval(this.refreshInterval);
            await this.processValidationStack();
        });
    }

    addToValidationStack(record, validationCallback) {
        const relevantStack = this.validationStack[record.resModel];
        if (relevantStack.find((rec) => rec.record.resId === record.resId)) {
            return; // Don't add more than once the same record into the stack.
        }
        relevantStack.push({
            record,
            isValidated: false,
            validationCallback,
        });
    }

    close() {
        this.homeMenu.toggle();
    }

    async _onBarcodeScanned(barcode) {
        if (barcode.startsWith("OBT") || barcode.startsWith("OCD")) {
            return;
        }
        const production = this.productions.find((mo) => mo.data.name === barcode);
        if (production) {
            return this._onProductionBarcodeScanned(barcode);
        }
        const workorder = this.relevantRecords.find((wo) => wo.data.barcode === barcode && wo.resModel === 'mrp.workorder');
        if (workorder) {
            return this._onWorkorderBarcodeScanned(workorder);
        }
        const employee = await this.orm.call("mrp.workcenter", "get_employee_barcode", [
            barcode,
        ]);
        if (employee) {
            return this.useEmployee.setSessionOwner(employee, undefined);
        }
    }

    async _onProductionBarcodeScanned(barcode){
        const searchItem = Object.values(this.env.searchModel.searchItems).find(
            (i) => i.fieldName === "name"
        );
        const autocompleteValue = {
            label: barcode,
            operator: "=",
            value: barcode,
        }
        this.env.searchModel.addAutoCompletionValues(searchItem.id, autocompleteValue);
    }

    async _onWorkorderBarcodeScanned(workorder){
        workorder.component.onClickHeader();
        this.env.reload(workorder);
    }

    get barcodeTargetRecord(){
        const currentAdminId = this.useEmployee.employees.admin.id;
        if (currentAdminId === this.adminId) {
            // We've already found the target record for the current admin, so we can return it
            return this.barcodeTargetRecordId;
        }
        const firstWorking = this.relevantRecords.find((r) => r.data.employee_ids.records.some((e) => e.resId === currentAdminId));
        this.adminId = currentAdminId;
        this.barcodeTargetRecordId = firstWorking ? firstWorking.resId : this.relevantRecords[0].resId;
        return this.barcodeTargetRecordId;
    }

    get productions() {
        return this.model.root.records;
    }

    get shouldHideNewWorkcenterButton() {
        return this.props.context.shouldHideNewWorkcenterButton || false;
    }

    get workorders() {
        // Returns all workorders
        return this.model.root.records.flatMap((mo) => mo.data.workorder_ids.records);
    }

    get filteredWorkorders() {
        // Returns all workorders, filtered by the currently selected states
        const activeStates = this.env.searchModel.state.workorderFilters.reduce(
            (acc, f) => (f.isActive ? [...acc, f.name] : acc),
            []
        );
        if (!activeStates.length) {
            return this.workorders;
        }
        return this.workorders.filter((wo) => activeStates.includes(wo.data.state));
    }

    toggleWorkcenter(workcenters) {
        const localStorageName = this.env.localStorageName;
        localStorage.setItem(localStorageName, JSON.stringify(workcenters));
        this.state.workcenters = workcenters;
        this.env.searchModel.setWorkcenterFilter(workcenters);
    }

    toggleEmployeesPanel() {
        this.state.showEmployeesPanel = !this.state.showEmployeesPanel;
        localStorage.setItem("mrp_workorder.show_employees", String(this.state.showEmployeesPanel));
    }

    getproduction(record) {
        if (record.resModel === "mrp.production") {
            return record;
        }
        return this.model.root.records.find((mo) => mo.resId === record.data.production_id[0]);
    }

    async processValidationStack() {
        const productionIds = [];
        const kwargs = {};
        for (const workorder of this.validationStack["mrp.workorder"]) {
            await workorder.validationCallback();
        }
        for (const production of this.validationStack["mrp.production"]) {
            if (!production.isValidated) {
                productionIds.push(production.record.resId);
                const { data } = production.record;
                if (data.product_tracking == "serial") {
                    kwargs.context = kwargs.context || { skip_redirection: true };
                    if (data.product_qty > 1) {
                        kwargs.context.skip_backorder = true;
                        if (!kwargs.context.mo_ids_to_backorder) {
                            kwargs.context.mo_ids_to_backorder = [];
                        }
                        kwargs.context.mo_ids_to_backorder.push(production.resId);
                    }
                }
            }
        }
        if (productionIds.length) {
            const action = await this.orm.call(
                "mrp.production",
                "button_mark_done",
                [productionIds],
                kwargs
            );
            if (action && typeof action === "object") {
                return this.actionService.doAction(action);
            }
            this.validationStack = {
                "mrp.production": [],
                "mrp.workorder": [],
            };
        }
        this.env.searchModel.invalidateRecordCache();
        return { success: true };
    }

    get relevantRecords() {
        const myWorkordersFilter = (wo) => this.adminWorkorderIds.includes(wo.resId) && wo.data.state != "cancel";
        const workcenterFilter = (wo) => wo.data.workcenter_id[0] === this.state.activeWorkcenter && wo.data.state != "cancel";
        const showMOs = this.state.activeResModel === "mrp.production";
        const filteredRecords = showMOs
            ? this.productions
            : this.filteredWorkorders.filter(
                  this.state.activeWorkcenter === -1 ? myWorkordersFilter : workcenterFilter
              );
        if (this.env.searchModel.recordCache.ids.length) {
            // Add any new records that conform to filter criteria but were not yet in the cache
            this.env.searchModel.recordCache.ids.push(
                ...filteredRecords.reduce(
                    (acc, rec) =>
                        this.env.searchModel.recordCache.ids.includes(rec.resId)
                            ? acc
                            : [...acc, rec.resId],
                    []
                )
            );
            const allRecordsHash = (showMOs ? this.productions : this.workorders).reduce(
                (acc, rec) => ({ ...acc, [rec.resId]: rec }),
                {}
            );
            // In some cases (ex. MO ready after scrap), an MO included in the filtered records at the previous load no
            // longer conforms to the current filterset.
            // We make sure this does not result in any undefined values in the returned list.
            return this.env.searchModel.recordCache.ids.reduce((acc, id) => {
                const record = allRecordsHash[id];
                return record ? [...acc, record] : acc;
            }, []);
        } else {
            // Put the filtered records in the cache as it is empty, and return the records
            if (!showMOs) {
                // Sort the filtered workorders first
                const statesComparativeValues = {
                    // Smallest value = first. Biggest value = last.
                    progress: 0,
                    ready: 1,
                    pending: 2,
                    waiting: 3,
                    finished: 4,
                };
                filteredRecords.sort((wo1, wo2) => {
                    const v1 = statesComparativeValues[wo1.data.state];
                    const v2 = statesComparativeValues[wo2.data.state];
                    const d1 = wo1.data.date_start;
                    const d2 = wo2.data.date_start;
                    return v1 - v2 || d1 - d2;
                });
            }
            this.env.searchModel.recordCache.ids = filteredRecords.map((r) => r.resId);
            return filteredRecords;
        }
    }

    get adminWorkorderIds() {
        const admin_id = this.useEmployee.employees.admin.id;
        if (!admin_id) {
            return [];
        }
        const admin = this.useEmployee.employees.connected.find((emp) => emp.id === admin_id);
        const workorderIds = admin ? new Set(admin.workorder.map((wo) => wo.id)) : new Set([]);
        for (const workorder of this.workorders) {
            if (workorder.data.employee_assigned_ids.resIds.includes(admin_id)) {
                workorderIds.add(workorder.resId);
            }
        }
        return [...workorderIds];
    }

    async selectWorkcenter(workcenterId, filterMO = false) {
        // Waits all the MO under validation are actually validated before to change the WC.
        const result = await this.processValidationStack();
        await this.useEmployee.getConnectedEmployees();
        if (result.success) {
            if (filterMO) {
                await this._onProductionBarcodeScanned(filterMO);
            } else {
                this.env.searchModel.invalidateRecordCache();
            }
            const workcencenterIds = this.state.workcenters.map((wc) => wc.id);
            this.state.activeWorkcenter = Number(workcenterId);
            this.state.activeResModel = this.state.activeWorkcenter
            ? "mrp.workorder"
            : "mrp.production";
            if (
                this.state.activeWorkcenter > 0 &&
                !workcencenterIds.includes(this.state.activeWorkcenter)
            ) {
                const workcenters = await this.orm.searchRead(
                    "mrp.workcenter", [], ["display_name"]
                );
                const workcenterToToggle = [
                    ...workcencenterIds,
                    this.state.activeWorkcenter,
                ].reduce((acc, id) => {
                    const res = workcenters.find((wc) => wc.id === id);
                    return res ? [...acc, res] : acc;
                }, []);
                this.toggleWorkcenter(workcenterToToggle);
            }
        }
    }

    async removeFromValidationStack(record, isValidated=true) {
        const relevantStack = this.validationStack[record.resModel];
        const foundRecord = relevantStack.find(rec => rec.record.resId === record.resId);
        if (isValidated) {
            foundRecord.isValidated = true;
            this.env.searchModel.removeRecordFromCache(record.resId);
            if (relevantStack.every((rec) => rec.isValidated)) {
                // Empties the validation stack if all under validation MO or WO are validated.
                this.validationStack[record.resModel] = [];
            }
        } else {
            const index = relevantStack.indexOf(foundRecord);
            relevantStack.splice(index, 1);
        }
    }

    toggleWorkcenterDialog(showWarning = true) {
        const params = {
            title: _t("Select Work Centers for this station"),
            confirm: this.toggleWorkcenter.bind(this),
            disabled: [],
            active: this.state.workcenters.map((wc) => wc.id),
            radioMode: false,
            showWarning: showWarning,
        };
        this.dialogService.add(MrpWorkcenterDialog, params);
    }

    _makeModelParams() {
        /// Define the structure for related fields
        const { resModel, fields } = this.props.models.find((m) => m.resModel === "mrp.production");
        const activeFields = [];
        for (const fieldName in fields) {
            activeFields[fieldName] = makeActiveField();
        }
        const params = {
            config: { resModel, fields, activeFields },
            limit: this.state.limit,
        };
        const workorderFields = this.props.models.find(
            (m) => m.resModel === "mrp.workorder"
        ).fields;
        params.config.activeFields.workorder_ids.related = {
            fields: workorderFields,
            activeFields: workorderFields,
        };
        const moveFields = this.props.models.find((m) => m.resModel === "stock.move").fields;
        const moveFieldsRelated = {
            fields: moveFields,
            activeFields: moveFields,
        };
        params.config.activeFields.move_raw_ids.related = moveFieldsRelated;
        params.config.activeFields.move_byproduct_ids.related = moveFieldsRelated;
        params.config.activeFields.move_finished_ids.related = moveFieldsRelated;
        const checkFields = this.props.models.find((m) => m.resModel === "quality.check").fields;
        params.config.activeFields.check_ids.related = {
            fields: checkFields,
            activeFields: checkFields,
        };
        params.config.activeFields.workorder_ids.related.activeFields.move_raw_ids.related = {
            fields: moveFields,
            activeFields: moveFields,
        };
        params.config.activeFields.workorder_ids.related.activeFields.check_ids.related = {
            fields: checkFields,
            activeFields: checkFields,
        };
        return params;
    }

    async onClickRefresh() {
        const result = await this.processValidationStack();
        if (result.success) {
            this.env.reload();
            this.env.searchModel.invalidateRecordCache();
        }
    }

    login() {
        this.useEmployee.popupAddEmployee();
        if (this.state.activeWorkcenter === -1) {
            this.env.searchModel.invalidateRecordCache();
        }
    }

    logout(id) {
        this.useEmployee.logout(id);
        if (this.state.activeWorkcenter === -1) {
            this.env.searchModel.invalidateRecordCache();
        }
    }

    changeAdmin(id) {
        this.useEmployee.toggleSessionOwner(id);
        if (this.state.activeWorkcenter === -1) {
            this.env.searchModel.invalidateRecordCache();
        }
    }

    _onPagerChanged({ offset, limit }) {
        this.state.offset = offset;
        this.state.limit = limit;
        this.env.searchModel.invalidateRecordCache();
        this.env.reload();
    }

    async loadSamples() {
        this.state.canLoadSamples = "disabled";
        await this.orm.call("mrp.production", "action_load_samples", [[]]);
        if (this.groups.workorders) {
            this.toggleWorkcenter([]);
            this.toggleWorkcenterDialog();
        }
        this.env.reload();
        this.state.canLoadSamples = false;
    }

    demoMORecords = [
        {
            id: 1,
            resModel: 'mrp.production',
            data: {
                product_id: [0, "[FURN_8522] Table Top"],
                product_tracking: "serial",
                product_qty: 4,
                product_uom_id: [1, "Units"],
                qty_producing: 4,
                state: "progress",
                move_raw_ids: {
                    records: [
                        {
                            resModel: "stock.move",
                            data: {
                                product_id: [0, "[FURN_7023] Wood Panel"],
                                product_uom_qty: 8,
                                product_uom: [1, "Units"],
                                manual_consumption: true,
                            }
                        }
                    ]
                },
                move_byproduct_ids: {records: []},
                workorder_ids: {
                    records: [
                        {
                            resModel: "mrp.workorder",
                            data: {
                                id: 1,
                                name: "Manual Assembly",
                                workcenter_id: [1, "Assembly 1"],
                                check_ids: {
                                    records: []
                                },
                                employee_ids: {records: []}
                            }
                        }
                    ]
                },
                display_name: "WH/MO/00013",
                check_ids: {records: []},
                employee_ids: {records: []},
                priority: "1"
            },
            fields: {
                state: {
                    selection: [["progress", "In Progress"]],
                    type: "selection"
                },
                priority:{
                    selection: [['0', 'Normal'],['1', 'Urgent']],
                    type: "selection"
                },
            },
        },
        {
            id: 2,
            resModel: 'mrp.production',
            data: {
                product_id: [0, "[D_0045_B] Stool (Dark Blue)"],
                product_tracking: "serial",
                product_qty: 1,
                product_uom_id: [1, "Units"],
                qty_producing: 1,
                state: "confirmed",
                move_raw_ids: {records: []},
                move_byproduct_ids: {records: []},
                workorder_ids: {
                    records: [
                        {
                            resModel: "mrp.workorder",
                            data: {
                                id: 1,
                                name: "Assembly  0/6",
                                workcenter_id: [2, "Assembly 2"],
                                check_ids: {
                                    records: []
                                },
                                employee_ids: {records: []}
                            }
                        }
                    ]
                },
                display_name: "WH/MO/00015",
                check_ids: {records: []},
                employee_ids: {records: []},
                priority: false
            },
            fields: {
                state: {
                    selection: [["confirmed", "Confirmed"]],
                    type: "selection"
                },
                priority:{
                    selection: [['0', 'Normal'],['1', 'Urgent']],
                    type: "selection"
                },
            },
        }
    ]
}
