/* @odoo-module */

import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";


export const patchAvatarCardResourcePopover = {
    async onWillStart() {
        this.hr_access = await user.hasGroup("hr.group_hr_user");
        await super.onWillStart();
    },
    loadAdditionalData() {
        const promises = super.loadAdditionalData();
        this.roles = [];
        if (this.record.role_ids?.length) {
            promises.push(
                this.orm
                    .read("planning.role", this.record.role_ids, ["name", "color"])
                    .then((roles) => {
                        this.roles = roles;
                    })
            );
        }
        return promises;
    },
    get fieldNames() {
        const additionalFields = ["role_ids"];
        const excludedFields = ["work_location_name", "work_location_type"];
        if (this.hr_access) {
            additionalFields.push("default_role_id");
        }
        return [
            ...super.fieldNames,
            ...additionalFields,
        ].filter((field) => !excludedFields.includes(field));
    },
    get roleTags() {
        return this.roles.map(({ id, color, name }) => ({
            id,
            colorIndex: color,
            text: name,
            icon: id === this.record.default_role_id?.[0] && this.roles.length > 1 && "fa-star",
            className: "o_planning_avatar_role_tag",
        }));
    },
};

export const unpatchAvatarCardResourcePopover = patch(AvatarCardResourcePopover.prototype, patchAvatarCardResourcePopover);
