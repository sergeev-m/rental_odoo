from odoo import models, fields, api


class Payout(models.Model):
    _name = "rental_vehicles.payout"
    _description = "Rental Vehicles Payout"
    _order = 'id desc'

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    office_id = fields.Many2one("rental_vehicles.office", string="Office", required=True)

    date_from = fields.Date("Date From", required=True)
    date_to = fields.Date("Date To", required=True)

    order_ids = fields.Many2many("rental_vehicles.order", string="Orders")
    manager_payout_ids = fields.One2many('rental_vehicles.manager.payout', 'payout_id')
    currency_id = fields.Many2one(
        "res.currency",
        related="office_id.currency_id",
        store=True,
    )
    salary_percent = fields.Float(related='office_id.salary_percent')
    salary_fixed_usd = fields.Float(related='office_id.salary_fixed_usd')
    
    currency_rate_snapshot = fields.Float(
        string="Exchange Rate Snapshot (USD → Office Currency)"
    )
    total_payout = fields.Monetary(
        string="Total Payout",
        compute="_compute_total_payout",
        currency_field="currency_id",
        store=True
    )

    @api.depends("manager_payout_ids.total_payout")
    def _compute_total_payout(self):
        for rec in self:
            rec.total_payout = sum(rec.manager_payout_ids.mapped('total_payout'))

    @api.depends('office_id', 'date_from')
    def _compute_name(self):
        for rec in self:
            if rec.date_from:
                rec.name = f"{rec.office_id.name}: {rec.date_from.strftime('%B %Y')}"
            else:
                rec.name = rec.office_id.name

    def action_recalculate(self):
        for rec in self:
            rec.write({'manager_payout_ids':[fields.Command.clear()]})

            rec.order_ids = self.env[rec.order_ids._name].search([
                ("office_id", "=", rec.office_id.id),
                ("start_date", ">=", rec.date_from),
                ("start_date", "<=", rec.date_to),
                ("status_code", "not in", ["draft", 'cancelled']),
            ])

            values = []
            order_grouped_list = rec.order_ids.grouped(key="create_uid")
            for manager, orders in order_grouped_list.items():
                m = rec.manager_payout_ids.create({
                    'manager_id': manager.id,
                    'order_ids': orders
                })
                values.append(m.id)
            rec.manager_payout_ids = [(6, 0, values)]

    def action_view_orders(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Заказы",
            "res_model": self['order_ids']._name,  # noqa
            "view_mode": "list,form",
            "domain": [("id", "in", self.order_ids.ids)],
            "context": {},
        }


class ManagerPayout(models.Model):
    _name = "rental_vehicles.manager.payout"
    _description = "Manager Payout for Period"

    payout_id = fields.Many2one("rental_vehicles.payout")
    manager_id = fields.Many2one("res.users", required=True, string="Manager")
    order_ids = fields.Many2many("rental_vehicles.order", string="Orders")
    currency_id = fields.Many2one(
        "res.currency",
        related="payout_id.currency_id"
    )
    revenue = fields.Monetary(
        "Revenue",
        currency_field="currency_id",
        compute='_compute_revenue',
        store=True
    )
    percent_part = fields.Monetary(
        "Percent Part",
        currency_field="currency_id",
        compute='_compute_percent_part',
        store=True
    )
    salary_fixed_converted = fields.Monetary(
        "Fixed Salary (Office Currency)",
        currency_field="currency_id",
        compute='_compute_salary_fixed_converted',
        help="Fixed salary converted from USD to the office currency.",
        store=True
    )
    total_payout = fields.Monetary(
        "Total (Office Currency)",
        currency_field="currency_id",
        compute='_compute_total_payout',
        store=True
    )

    @api.depends('order_ids.amount_total')
    def _compute_revenue(self):
        for rec in self:
            rec.revenue = sum(rec.order_ids.mapped('amount_total'))

    @api.depends('revenue', 'payout_id.salary_percent')
    def _compute_percent_part(self):
        for rec in self:
            rec.percent_part = rec.revenue  * (rec.payout_id.salary_percent / 100)

    @api.depends('payout_id.salary_fixed_usd', 'payout_id.currency_rate_snapshot')
    def _compute_salary_fixed_converted(self):
        for rec in self:
            p = rec.payout_id
            rec.salary_fixed_converted = p.salary_fixed_usd * p.currency_rate_snapshot

    @api.depends("percent_part", "salary_fixed_converted")
    def _compute_total_payout(self):
        for rec in self:
            rec.total_payout = rec.percent_part + rec.salary_fixed_converted
