# Copyright 2014-2015 Grupo ESOC (<http://www.grupoesoc.es>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import _, exceptions


class EmptyNamesError(exceptions.ValidationError):
    def __init__(self, record, value=None):
        value = value or _("No name is set.")
        self.record = record
        self._value = value
        self._name = _("Error(s) with partner %d's name.") % record.id
        self.args = (self._name, value)
