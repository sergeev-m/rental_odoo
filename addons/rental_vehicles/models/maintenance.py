from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RentalMaintenance(models.Model):
    _name = "rental_vehicles.maintenance"
    _description = "Maintenance"
    _order = 'id desc'

    name = fields.Char(compute='_compute_name')
    vehicle_id = fields.Many2one("rental_vehicles.vehicle", string="Vehicle", required=True)
    date = fields.Date(default=fields.Date.today, index=True)
    mileage = fields.Integer(required=True)
    note = fields.Text("Notes")

    maintenance_line_ids = fields.One2many("rental_vehicles.maintenance.line", "maintenance_id", string="Maintenance Lines")
    total_cost = fields.Float("Total Cost", compute="_compute_total_cost", store=True)
    currency_id = fields.Many2one(related='vehicle_id.office_id.currency_id')

    @api.depends('maintenance_line_ids')
    def _compute_name(self):
        for rec in self:
            names = [
                name
                for name in rec.maintenance_line_ids.mapped('service_type_id.name')
                if isinstance(name, str)
            ]

            rec.name = '/'.join(names)

    @api.depends("maintenance_line_ids.cost")
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = sum(rec.maintenance_line_ids.mapped('cost'))

    @api.constrains("mileage")
    def _check_mileage(self):
        for rec in self:
            if rec.mileage <= 0 or rec.mileage > rec.vehicle_id.mileage:
                raise ValidationError("Не указан пробег в сервисном обслуживании или пробег больше реального...")

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.mileage = self.vehicle_id.mileage


class RentalMaintenanceLine(models.Model):
    _name = "rental_vehicles.maintenance.line"
    _description = "Maintenance Line"

    maintenance_id = fields.Many2one("rental_vehicles.maintenance", string="Maintenance", ondelete="cascade")
    service_type_id = fields.Many2one("rental_vehicles.service.type", string="Service Type", required=True)
    cost = fields.Float("Cost")

    @api.onchange('service_type_id')
    def _onchange_service_type_id(self):
        for rec in self:
            if rec.service_type_id and not rec.cost:
                rec.cost = rec.service_type_id.default_cost
