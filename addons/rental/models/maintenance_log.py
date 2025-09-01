from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RentalMaintenanceLog(models.Model):
    _name = "rental.maintenance.log"
    _description = "Maintenance Log"

    name = fields.Char(compute='_compute_name')
    vehicle_id = fields.Many2one("rental.vehicle", string="Vehicle", required=True)
    date = fields.Date(default=fields.Date.today, index=True)
    mileage = fields.Integer(required=True)
    note = fields.Text("Notes")

    cost_line_ids = fields.One2many("rental.maintenance.cost.line", "log_id", string="Cost Lines")
    total_cost = fields.Float("Total Cost", compute="_compute_total_cost", store=True)
    currency_id = fields.Many2one(related='vehicle_id.office_id.currency_id')

    @api.depends('cost_line_ids')
    def _compute_name(self):
        for rec in self:
            cost_list = rec.cost_line_ids.mapped('service_type_id.name')
            rec.name = '/'.join(cost_list)

    @api.depends("cost_line_ids.cost")
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.cost_line_ids.mapped('cost'))

    @api.constrains("mileage")
    def _check_mileage(self):
        for rec in self:
            if rec.mileage <= 0 or rec.mileage > rec.vehicle_id.mileage:
                raise ValidationError("Не указан пробег в сервисном обслуживании или пробег больше реального...")

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.mileage = self.vehicle_id.mileage


class RentalMaintenanceCostLine(models.Model):
    _name = "rental.maintenance.cost.line"
    _description = "Maintenance Cost Line"

    log_id = fields.Many2one("rental.maintenance.log", string="Maintenance Log", ondelete="cascade")
    service_type_id = fields.Many2one("rental.service.type", string="Service Type", required=True)
    cost = fields.Float("Cost")

    @api.onchange('service_type_id')
    def _onchange_service_type_id(self):
        for rec in self:
            if rec.service_type_id and not rec.cost:
                rec.cost = rec.service_type_id.default_cost
