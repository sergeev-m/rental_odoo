from logging import getLogger
from pprint import pformat
from datetime import timedelta
from typing import Literal
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime


_logger = getLogger(__name__)


ORDER_LINE_TYPE_SELECTION = [
    ("tariff", "Tariff"),
    ("accessory", "Accessory Rental"),
    ("manual", "Manual"),
    ("penalty", "Penalty"),
    ("sale", "Sale"),
    ("discount", "Discount / Refund"),
]

ORDER_LINE_TYPES = {i[0] for i in ORDER_LINE_TYPE_SELECTION}
SALARY_LINE_TYPES = {'tariff', 'accessory', 'manual', 'discount'}

assert not (SALARY_LINE_TYPES - ORDER_LINE_TYPES), f"Invalid SALARY_LINE_TYPES, should be {ORDER_LINE_TYPES}"

ORDER_LINE_SEQUENCE = {
    "tariff": 10,
    "manual": 20,
    "accessory": 30,
    "sale": 30,
    "discount": 50,
    "penalty": 60,
}


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
    _inherit = ['rental_vehicles.office.mixin']
    _description = "Rental Vehicles Order"
    _order = "start_date desc"

    name = fields.Char(compute='_compute_name', store=True)
    active = fields.Boolean(default=True)
    vehicle_id = fields.Many2one(
        "rental_vehicles.vehicle",
        # required=True,
        domain="[('office_id', '=', office_id), ('status', '=', 'available')]"
    )
    renter_id = fields.Many2one('rental_vehicles.renter')
    rental_days = fields.Integer(required=True, default=1)
    rental_hours = fields.Integer()
    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(string="End Date", compute="_compute_end_date", store=True)
    start_mileage = fields.Integer()
    end_mileage = fields.Integer()
    currency_id = fields.Many2one(related='office_id.currency_id')
    amount_total = fields.Monetary(currency_field="currency_id", compute="_compute_amount", store=True)
    amount_salary_base = fields.Monetary(compute='_compute_amount', store=True)
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

    progress_percent = fields.Integer(compute="_compute_progress", store=False)
    progress_label = fields.Char(compute="_compute_progress", store=False)
    progress_html = fields.Html(compute="_compute_progress_html", sanitize=False)

    order_line_ids = fields.One2many(
        "rental_vehicles.order.line",
        "order_id",
        string="Order Lines",
    )

    def _create_update_tariff_lines(self, period_type: Literal['hour', 'day']):
        self.ensure_one()

        if not self.vehicle_id:
            return

        f_name = f'rental_{period_type}s'
        tariff_filter = (
            lambda r: r.type == "tariff"
            and r.tariff_id.period_type == period_type
        )
        tariff_line = self.order_line_ids.filtered(tariff_filter)

        if self[f_name] == 0:
            self.order_line_ids = self.order_line_ids - tariff_line
            return

        tariff = self.env['rental_vehicles.tariff'].search([
            ('vehicle_model_id', '=', self.vehicle_model_id.id),
            ('period_type', '=', period_type),
            ('min_period', '<=', self[f_name]),
            ('office_id', '=', self.office_id.id)
        ], order='min_period desc', limit=1)
        
        if not tariff:
            return

        values = {
            'tariff_id': tariff.id,
            'name': tariff.name,
            'price': tariff.price_per_unit,
        }

        if tariff_line and tariff_line.tariff_id != tariff.id:
            tariff_line.update(values)
            return

        values = {
            **values,
            "order_id": self.id,
            "type": "tariff",
        }
        self.order_line_ids.new({**values})

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        self.start_mileage = False
        if self.vehicle_id:
            self.start_mileage = self.vehicle_id.mileage
    
    @api.onchange('rental_hours')
    def _onchange_rental_hours(self):
        self._create_update_tariff_lines('hour')

    @api.onchange('rental_days', 'vehicle_id')
    def _onchange_rental_days(self):
        self._create_update_tariff_lines('day')

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
        
    @api.depends(
        'order_line_ids',
        'order_line_ids.total',
        'order_line_ids.type'
    )
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = sum(rec.order_line_ids.mapped('total'))
            
            rec.amount_salary_base = sum(
                line.total
                for line in rec.order_line_ids
                if line.affects_salary
            )

    def action_start_rental(self):
        for rec in self:
            if rec.status_code != "draft":
                raise ValidationError("должен быть статус draft")
        active = self.status_id._active_status
        self.status_id = active.id
        if self.vehicle_id:
            self.vehicle_id.status = "rented"

    def action_end_rental(self):
        for rec in self:
            if rec.status_code != "active":
                raise ValidationError("Завершить можно только активную аренду.")
        done = self.status_id._done_status
        self.status_id = done.id
        if self.vehicle_id:
            self.vehicle_id.mileage = max(
                self.vehicle_id.mileage, self.end_mileage
            )
            self.vehicle_id.status = "available"

    def action_cancel(self):
        for rec in self:
            if rec.status_code not in ("draft", "active"):
                raise ValidationError("Отменить можно только черновик или активную аренду.")
            if rec.status_code == "active" and self.vehicle_id:
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

    @api.depends('vehicle_id', 'order_line_ids')
    def _compute_name(self):
        for rec in self:
            values = [rec.id]
            
            if rec.vehicle_id:
                values = (rec.vehicle_id.name,)
            else:
                filter_domain = [
                    ('type', 'in', ('accessory', 'sale')),
                    ('accessory_id', '!=', False)
                ]
                order_lines = rec.order_line_ids.filtered_domain(filter_domain)
                values = order_lines.mapped('accessory_id.name')

            placeholder = ' '.join(['%s'] * len(values))
            rec.name = placeholder % tuple(values) if values else False

    def write(self, vals):
        old_vehicle_id = self.vehicle_id.id
        res = super(RentalVehiclesOrder, self).write(vals)

        if old_vehicle_id != self.vehicle_id.id and self.status_code == "active":
            old_vehicle = self.env[self.vehicle_id._name].browse(old_vehicle_id)
            old_vehicle.status = 'available'
            self.vehicle_id.status = 'rented'
            self._log([f'{v.name}: {v.status}' for v in (old_vehicle, self.vehicle_id)])

        return res

    def _log(self, vals, *, level='debug', pad: int = 2, title: str | None = None):
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

        getattr(_logger, level)(final)

    @api.depends("start_date", "end_date")
    def _compute_progress(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.start_date and rec.end_date:
                total = (rec.end_date - rec.start_date).total_seconds()
                passed = (now - rec.start_date).total_seconds()
                rec.progress_percent = int(max(0, min(100, passed / total * 100)))
            else:
                rec.progress_percent = 0

            if rec.end_date:
                rec.progress_label = format_datetime(
                    rec.env,
                    rec.end_date,
                    tz=rec.env.user.tz or "UTC",
                    lang_code="ru_RU",
                    dt_format="d MMM HH:mm"
                )
            else:
                rec.progress_label = ""

    @api.depends("progress_percent", "progress_label", 'end_date')
    def _compute_progress_html(self):
        now = fields.Datetime.now()
        for rec in self:
            color = "#adb5bd"

            if rec.status_id == rec.status_id._active_status:
                if rec.end_date:
                    if rec.end_date < now:
                        color = "#dc3545"  # красный (просрочено)
                    elif (rec.end_date - now).total_seconds() < 6 * 3600:
                        color = "#fd7e14"  # оранжевый (скоро заканчивается)
                    else:
                        color = "#2f80ed"  # синий (в норме)
                else:
                    color = "#2f80ed"

            width = rec.progress_percent

            rec.progress_html = f"""
            <div style='width:100%; background:#e9ecef; height:14px; border-radius:4px; position:relative;'>
                <div style='width:{width}%; background:{color}; height:100%; border-radius:4px;'></div>

                <span style='position:absolute; left:50%; top:-2px; 
                             transform:translateX(-50%);
                             font-size:11px; color:#333; white-space:nowrap;'>
                    {rec.progress_label}
                </span>
            </div>
            """

    @api.onchange('order_line_ids')
    def _onchange_order_lines(self):
        lines = self.order_line_ids.filtered(
            lambda l: l.type == "tariff" and l.tariff_id.exists()
        )

        if not lines.exists():
            return

        values = {'rental_days': 0, 'rental_hours': 0}
        for line in lines:
            values.pop(f'rental_{line.tariff_id.period_type}s')
            # values[f'rental_{line.tariff_id.period_type}s'] = line.quantity
        self.update(values)

    def _apply_period(self, period_type: Literal['hour', 'day'], quantity):
        f_name =  f'rental_{period_type}s'
        self.write({f_name: quantity})


class OrderLine(models.Model):
    _name = "rental_vehicles.order.line"
    _description = "Order Line"
    _order = "sequence asc, id asc"

    name = fields.Char()
    order_id = fields.Many2one("rental_vehicles.order")
    sequence = fields.Integer(
        compute="_compute_sequence",
        store=True,
        index=True,
    )

    type = fields.Selection(ORDER_LINE_TYPE_SELECTION, required=True)
    accessory_id = fields.Many2one(
        "rental_vehicles.accessory",
        string="Accessory"
    )
    office_id = fields.Many2one(related='order_id.office_id')
    vehicle_model_id = fields.Many2one(related='order_id.vehicle_model_id')
    tariff_id = fields.Many2one(
        "rental_vehicles.tariff",
        string="Tariff",
        domain="[('office_id', '=', office_id), ('vehicle_model_id', '=', vehicle_model_id)]",
    )

    quantity = fields.Float('qty', default=1)
    price = fields.Monetary()
    total = fields.Monetary(compute="_compute_total", store=True)
    currency_id = fields.Many2one(related="order_id.currency_id")

    affects_salary = fields.Boolean(
        string="Affects Manager Salary",
        compute='_compute_affects_salary',
        store=True
    )

    @api.depends("type")
    def _compute_sequence(self):
        for rec in self:
            rec.sequence = ORDER_LINE_SEQUENCE.get(rec.type, 42)

    @api.depends(
        "price",
        "quantity",
        "type",
        "order_id.rental_days",
        "order_id.rental_hours",
        "tariff_id.period_type",
    )
    def _compute_total(self):
        for rec in self:
            period = 1
            
            if rec.type == "tariff":
                order = rec.order_id
                if rec.tariff_id and rec.tariff_id.period_type == "hour":
                    period = max(order.rental_hours, period)
                else:
                    period = max(order.rental_days, period)

            elif rec.type == "accessory":
                period = max(rec.order_id.rental_days, period)

            rec.total = rec.price * rec.quantity * period

    @api.onchange("accessory_id")
    def _onchange_accessory_id(self):
        if self.accessory_id:
            self.name = self.accessory_id.name
            self.price = self.accessory_id.default_price

    @api.onchange('tariff_id')
    def _onchange_tariff_id(self):
        self.name = self.tariff_id.name
        self.price = self.tariff_id.price_per_unit

    @api.depends('type', 'accessory_id.affects_salary')
    def _compute_affects_salary(self):
        for rec in self:
            rec.affects_salary = (
                rec.type in SALARY_LINE_TYPES
                or rec.accessory_id and rec.accessory_id.affects_salary
            )

    def unlink(self):
        self._sync_rental_period()
        return super().unlink()

    def _sync_rental_period(self):
        for line in self.filtered(
            lambda l: l.type == "tariff" and self.tariff_id.exists()
        ):
            order = line.order_id
            period_type = line.tariff_id.period_type
            order._apply_period(period_type, 0)

    def write(self, vals):
        if (
            vals.get("type") == "discount"
            or ("type" not in vals and self.type == "discount")
        ):
            if "price" in vals:
                vals["price"] = -abs(vals["price"])
        return super().write(vals)

    @api.model
    def create(self, vals):
        if isinstance(vals, list):
            for v in vals:
                if v.get("type") == "discount" and "price" in v:
                    v["price"] = -abs(v["price"])
            return super().create(vals)

        if vals.get("type") == "discount" and "price" in vals:
            vals["price"] = -abs(vals["price"])
        return super().create(vals)
