/** @odoo-module **/

export const REINSERT_DYNAMIC_PIVOT_CHILDREN = (env) =>
    env.model.getters.getPivotIds().map((pivotId, index) => ({
        id: `reinsert_dynamic_pivot_${env.model.getters.getPivotFormulaId(pivotId)}`,
        name: env.model.getters.getPivotDisplayName(pivotId),
        sequence: index,
        execute: async (env) => {
            const { type } = env.model.getters.getPivotCoreDefinition(pivotId);
            const position = env.model.getters.getActivePosition();
            let table;
            if (type === "ODOO") {
                const dataSource = env.model.getters.getPivot(pivotId);
                const model = await dataSource.copyModelWithOriginalDomain();
                table = model.getTableStructure().export();
            } else {
                table = env.model.getters.getPivot(pivotId).getTableStructure().export();
            }
            env.model.dispatch("INSERT_PIVOT_WITH_TABLE", {
                ...position,
                pivotId,
                table,
                pivotMode: "dynamic",
            });
            env.model.dispatch("REFRESH_PIVOT", { id: pivotId });
        },
        isVisible: (env) => env.model.getters.getPivot(pivotId).isValid(),
    }));

export const REINSERT_STATIC_PIVOT_CHILDREN = (env) =>
    env.model.getters.getPivotIds().map((pivotId, index) => ({
        id: `reinsert_static_pivot_${env.model.getters.getPivotFormulaId(pivotId)}`,
        name: env.model.getters.getPivotDisplayName(pivotId),
        sequence: index,
        execute: async (env) => {
            const { type } = env.model.getters.getPivotCoreDefinition(pivotId);
            const position = env.model.getters.getActivePosition();
            let table;
            if (type === "ODOO") {
                const dataSource = env.model.getters.getPivot(pivotId);
                const model = await dataSource.copyModelWithOriginalDomain();
                table = model.getTableStructure().export();
            } else {
                table = env.model.getters.getPivot(pivotId).getTableStructure().export();
            }
            env.model.dispatch("INSERT_PIVOT_WITH_TABLE", {
                ...position,
                pivotId,
                table,
                pivotMode: "static",
            });
            env.model.dispatch("REFRESH_PIVOT", { id: pivotId });
        },
        isVisible: (env) => env.model.getters.getPivot(pivotId).isValid(),
    }));
