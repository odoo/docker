export const DocumentsControllerMixin = (component) =>
    class extends component {
        get modelParams() {
            const modelParams = super.modelParams;

            // Temporary fix to add fields to view. todo: remove in master
            Object.assign(modelParams.config.activeFields, {
                alias_domain_id: modelParams.config.activeFields.alias_domain_id ||  { ...modelParams.config.activeFields.owner_id }, // m2o
                alias_name: modelParams.config.activeFields.alias_name ||  { ...modelParams.config.activeFields.name }, // char
                alias_tag_ids: modelParams.config.activeFields.alias_tag_ids ||  { ...modelParams.config.activeFields.tag_ids }, // m2m
                file_size: modelParams.config.activeFields.file_size || { ...modelParams.config.activeFields.id }, // readonly int
                res_name: modelParams.config.activeFields.res_name || { ...modelParams.config.activeFields.name, readonly: true }, // char
            });
            modelParams.multiEdit = true;
            return modelParams;
        }
    };
