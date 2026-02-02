from odoo import models, fields, api, tools
from odoo.tools import frozendict


class ResUsers(models.Model):
    _inherit = ['res.users']

    office_id = fields.Many2one(
        "rental_vehicles.office",
        string="Office",
    )

    office_ids = fields.Many2many(
        "rental_vehicles.office",
        string="Allowed offices",
    )

    @api.model
    # @tools.ormcache('self.env.uid')
    def context_get(self):
        user = self.env.user
        ctx = dict(super().context_get())
        ctx.update({
            "allowed_office_ids": user.office_ids.ids,
            "office_id": user.office_ids[:1].id if user.office_ids else False,
        })
        return frozendict(ctx)
