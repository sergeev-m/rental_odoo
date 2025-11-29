from logging import getLogger
from pprint import pformat
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


_logger = getLogger(__name__)


class StatusBarOrder(models.Model):
    _name = "rental_vehicles.order.status"
    _order = "sequence"
    _description = "This is status of order."

    sequence = fields.Integer("Sequence", default=10)
    name = fields.Char("Status")
    code = fields.Char("Code")
    decoration = fields.Selection([
        ("success", "Success"),
        ("danger", "Danger"),
        ("warning", "Warning"),
        ("info", "Info"),
    ])

    def _search_by_code(self, code: str):
        rec = self.search([('code', '=', code)], limit=1)
        return rec

    @property
    def _active_status(self):
        return self._search_by_code('active')

    @property
    def _done_status(self):
        return self._search_by_code('done')

    @property
    def _cancelled_status(self):
        return self._search_by_code('cancelled')

    def _prepare_code(self, vals: dict):
        if code := vals.get('code'):
            vals['code'] = code.lower()
        return vals

    def create(self, vals):
        vals = self._prepare_code(vals)
        rec = super(StatusBarOrder, self).create(vals)
        return rec

    def write(self, vals):
        vals = self._prepare_code(vals)
        return super(StatusBarOrder, self).write(vals)


class RentalVehiclesOrder(models.Model):
    _name = "rental_vehicles.order"
    _description = "Rental Vehicles Order"
    _order = "start_date desc"

    active = fields.Boolean(default=True)
    office_id = fields.Many2one('rental_vehicles.office')
    vehicle_id = fields.Many2one(
        "rental_vehicles.vehicle",
        required=True,
        domain="[('office_id', '=', office_id), ('status', '=', 'available')]"
    )
    renter_id = fields.Many2one('rental_vehicles.renter')
    rental_days = fields.Integer(required=True, default=1)
    rental_hours = fields.Integer()
    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(string="End Date", compute="_compute_end_date", store=True)
    extra_expenses = fields.Float(string="Extra Expenses", default=0.0)
    start_mileage = fields.Integer()
    end_mileage = fields.Integer()
    currency_id = fields.Many2one(related='tariff_id.currency_id')
    amount_total = fields.Monetary(currency_field="currency_id", compute="_compute_amount_total", store=True)
    deposit_amount = fields.Float()
    
    status_id = fields.Many2one(
        "rental_vehicles.order.status",
        "Status",
        default=lambda self: self.env["rental_vehicles.order.status"].search(
            [("code", "=ilike", "draft")],
            limit=1
        )
    )
    status_decoration = fields.Selection(related="status_id.decoration")
    status_code = fields.Char(
        string="Status Code",
        related="status_id.code",
        store=True,
    )

    vehicle_type_id = fields.Many2one(
        related="vehicle_id.vehicle_type_id",
        store=True,
        readonly=True,
    )
    vehicle_model_id = fields.Many2one(
        related="vehicle_id.model_id",
        store=True,
        readonly=True,
    )
    tariff_id = fields.Many2one(
        "rental_vehicles.tariff",
        string="Tariff",
        required=True,
        domain="[('office_id', '=', office_id), ('vehicle_model_id', '=', vehicle_model_id)]",
    )
    tariff_price = fields.Monetary(
        string="Tariff Price",
        currency_field="currency_id",
        # readonly=True
    )

    @api.onchange('tariff_id')
    def _onchange_tarif_id(self):
        if self.status_code =='done':
            return

        if self.tariff_id:
            self.tariff_price = self.tariff_id.price_per_unit

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        self.start_mileage = False
        if self.vehicle_id:
            self.start_mileage = self.vehicle_id.mileage
    
    @api.onchange('rental_hours')
    def _onchange_rental_hours(self):
        if self.rental_days:
            return

        if not (self.vehicle_id and self.rental_hours):
            return

        self.tariff_id = False
        tariff = self.env['rental_vehicles.tariff'].search([
            ('vehicle_model_id', '=', self.vehicle_model_id.id),
            ('period_type', '=', 'hour'),
        ], limit=1)
        self.tariff_id = tariff.id if tariff else False

    @api.onchange('rental_days', 'vehicle_id')
    def _onchange_rental_days(self):
        self.tariff_id = False

        if not (self.vehicle_id and self.rental_days):
            return

        tariff = self.env['rental_vehicles.tariff'].search([
            ('vehicle_model_id', '=', self.vehicle_model_id.id),
            ('period_type', '=', 'day'),
            ('min_period', '<=', self.rental_days),
        ], order='min_period desc', limit=1)

        self.tariff_id = tariff.id if tariff else False

    @api.depends("start_date", "rental_days")
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date:
                end_dt = rec.start_date + timedelta(days=rec.rental_days)

                if end_dt.minute and end_dt.minute >= 5:
                    end_dt = end_dt + timedelta(hours=1)
                
                end_dt = end_dt.replace(minute=0, second=0, microsecond=0)
                rec.end_date = end_dt
            else:
                rec.end_date = False
        
    @api.depends('rental_days', 'rental_hours', 'tariff_price', 'extra_expenses')
    def _compute_amount_total(self):
        for rec in self:
            total = 0

            if rec.tariff_price and rec.rental_days:
                total = rec.rental_days * rec.tariff_price

            if rec.rental_hours:
                tariff_hour = rec.env['rental_vehicles.tariff'].search([
                    ('vehicle_model_id', '=', rec.vehicle_id.model_id.id),
                    ('period_type', '=', 'hour'),
                ], limit=1)
                if tariff_hour:
                    total += rec.rental_hours * tariff_hour.price_per_unit
            
            if rec.extra_expenses:
                total += rec.extra_expenses

            rec.amount_total = total

    def action_start_rental(self):
        for rec in self:
            if rec.status_code != "draft":
                raise ValidationError("должен быть статус draft")
        active = self.status_id._active_status
        self.status_id = active.id
        self.vehicle_id.status = "rented"

    def action_end_rental(self):
        for rec in self:
            if rec.status_code != "active":
                raise ValidationError("Завершить можно только активную аренду.")
        done = self.status_id._done_status
        self.status_id = done.id
        self.vehicle_id.mileage = max(self.vehicle_id.mileage, self.end_mileage)
        self.vehicle_id.status = "available"

    def action_cancel(self):
        for rec in self:
            if rec.status_code not in ("draft", "active"):
                raise ValidationError("Отменить можно только черновик или активную аренду.")
            if rec.status_code == "active":
                rec.vehicle_id.status = "available"
            cancelled = self.status_id._cancelled_status
            rec.status_id = cancelled.id

    def action_open_photo_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Recognize Renter from Photo",
            "res_model": "rental_vehicles.renter.photo.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }


    def _compute_display_name(self):
        for rec in self:
            values = (
                rec.id,
                rec.vehicle_id.name,
            )
            placeholder = ' '.join(['%s'] * len(values))
            rec.display_name = placeholder % tuple(values) if values else False

    def write(self, vals):
        old_vehicle_id = self.vehicle_id.id
        res = super(RentalVehiclesOrder, self).write(vals)

        if old_vehicle_id != self.vehicle_id.id and self.status_code == "active":
            old_vehicle = self.env[self.vehicle_id._name].browse(old_vehicle_id)
            old_vehicle.status = 'available'
            self.vehicle_id.status = 'rented'
            self._log([f'{v.name}: {v.status}' for v in (old_vehicle, self.vehicle_id)])

        return res


    def _log(self, vals, pad: int = 2, title: str | None = None):
        pretty = pformat(vals, width=120, compact=False)
        lines = pretty.splitlines() or [""]

        if title:
            lines = [title] + [""] + lines

        max_len = max(len(line) for line in lines)

        center_top = "◥◣◆◢◤"
        center_bottom = "◢◤◆◥◣"
        inner_width = (max_len + pad * 2 - len(center_top)) // 2
        side = "━" * inner_width
        total_inner = inner_width * 2 + len(center_top)

        top = f"┏{side}{center_top}{side}┓"
        bottom = f"┗{side}{center_bottom}{side}┛"

        inside_lines = []
        for line in lines:
            raw = " " * pad + line.ljust(max_len) + " " * pad
            centered = raw.center(total_inner)
            inside_lines.append(centered)

        inside = "\n".join(inside_lines)

        ascii_cat = [
            "  ∧,,,∧   ||",
            " ( • · •) ||",
            "  / づ    || ",
            ""
        ]

        center_pos = len(bottom) // 2 + len(bottom) % 2 + 1
        ascii_right = "\n".join(s.rjust(center_pos) for s in ascii_cat)

        final = "\n" + top + "\n" + inside + "\n" + bottom + "\n" + ascii_right

        _logger.debug(final)
