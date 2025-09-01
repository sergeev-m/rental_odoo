from odoo import models, fields, api, tools


class MaintenanceDueView(models.Model):
    _name = "rental.maintenance.due"
    _description = "Maintenance Due (SQL View)"
    _auto = False
    _rec_name = "vehicle_id"

    vehicle_id = fields.Many2one("rental.vehicle", readonly=True, index=True)
    office_id = fields.Many2one("rental.office", readonly=True)
    model_id = fields.Many2one("rental.vehicle.model", readonly=True)

    service_type_id = fields.Many2one("rental.service.type", string="Service Type")
    
    last_service_date = fields.Date(readonly=True)
    last_service_mileage = fields.Integer(readonly=True)

    next_service_date = fields.Date(readonly=True)
    next_service_mileage = fields.Integer(readonly=True)

    current_mileage = fields.Integer(readonly=True)
    km_to_due = fields.Integer(readonly=True)
    days_to_due = fields.Integer(readonly=True)

    is_due = fields.Boolean(readonly=True)
    overdue = fields.Boolean(readonly=True)
    color = fields.Integer(readonly=True)

    def action_perform_service(self):
        """Создаём запись в журнале обслуживания, обновляем состояние"""
        self.ensure_one()
        service_type = self.env['rental.service.type'].search(
            [('id', '=', self.service_type_id.id)],
            limit=1
        )
        log = self.env["rental.maintenance.log"].create({
            'vehicle_id': self.vehicle_id.id,
            'mileage': self.current_mileage,
            'note': f'ТО ({self.service_type_id.name})',
            'cost_line_ids': [(0, 0, {
                'service_type_id': service_type.id,
                'cost': service_type.default_cost,
            })]
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "rental.maintenance.log",
            "res_id": log.id,
            "view_mode": "form",
            "target": "current",
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, "rental_maintenance_due")
        self.env.cr.execute("""
            CREATE VIEW rental_maintenance_due AS
            WITH last_log AS (
                SELECT DISTINCT ON (l.vehicle_id, cl.service_type_id)
                       l.vehicle_id,
                       cl.service_type_id,
                       l.date        AS service_date,
                       l.mileage     AS mileage,
                       cl.id
                FROM rental_maintenance_cost_line cl
                JOIN rental_maintenance_log l ON l.id = cl.log_id
                ORDER BY l.vehicle_id, cl.service_type_id, l.date DESC, cl.id DESC
            )
            SELECT
                (v.id * 100000 + st.id) AS id,
                v.id AS vehicle_id,
                -- v.name AS vehicle_name,
                v.office_id AS office_id,
                v.model_id AS model_id,
                st.id AS service_type_id,

                COALESCE(ll.service_date, v.create_date::date) AS last_service_date,
                COALESCE(ll.mileage, 0) AS last_service_mileage,

                -- Дата следующего ТО
                (
                    CASE
                        WHEN mst.interval_days > 0 THEN
                            (
                                COALESCE(ll.service_date, v.create_date::date)
                                + (mst.interval_days || ' days')::interval
                            )::date
                        ELSE NULL
                    END
                ) AS next_service_date,

                -- Пробег следующего ТО
                (
                    CASE
                        WHEN mst.interval_km > 0 THEN
                            COALESCE(ll.mileage, 0) + mst.interval_km
                        ELSE NULL
                    END
                ) AS next_service_mileage,

                v.mileage AS current_mileage,

                -- Остаток до ТО по пробегу
                (
                    CASE
                        WHEN mst.interval_km > 0 THEN
                            (COALESCE(ll.mileage, 0) + mst.interval_km) - v.mileage
                        ELSE NULL
                    END
                ) AS km_to_due,

                -- Остаток до ТО по дням
                (
                    CASE
                        WHEN mst.interval_days > 0 THEN
                            (
                              (
                                COALESCE(ll.service_date, v.create_date::date)
                                + (mst.interval_days || ' days')::interval
                              )::date - CURRENT_DATE
                            )
                        ELSE NULL
                    END
                ) AS days_to_due,

                -- Флаги "пора" и "просрочено"
                (
                    CASE
                      WHEN (mst.interval_km > 0 AND (COALESCE(ll.mileage,0)+mst.interval_km - v.mileage) <= mst.remind_before_km)
                        OR (mst.interval_days > 0 
                            AND (
                                (COALESCE(ll.service_date, v.create_date::date) + (mst.interval_days || ' days')::interval)::date - CURRENT_DATE
                            ) <= mst.remind_before_days)
                      THEN TRUE ELSE FALSE
                    END
                ) AS is_due,

                (
                    CASE
                      WHEN (mst.interval_km > 0 AND v.mileage > COALESCE(ll.mileage,0)+mst.interval_km)
                        OR (mst.interval_days > 0 AND (
                            (COALESCE(ll.service_date, v.create_date::date) + (mst.interval_days || ' days')::interval)::date
                          ) > CURRENT_DATE)
                      THEN TRUE ELSE FALSE
                    END
                ) AS overdue,

                (
                    CASE
                      WHEN (mst.interval_km > 0 AND (COALESCE(ll.mileage,0)+mst.interval_km - v.mileage) < 0)
                        OR (mst.interval_days > 0 AND (
                            (COALESCE(ll.service_date, v.create_date::date) + (mst.interval_days || ' days')::interval)::date - CURRENT_DATE
                          ) <= 0)
                      THEN 1
                      WHEN (mst.interval_km > 0 AND (COALESCE(ll.mileage,0)+mst.interval_km - v.mileage) <= mst.remind_before_km)
                        OR (mst.interval_days > 0 
                            AND (
                                (COALESCE(ll.service_date, v.create_date::date) + (mst.interval_days || ' days')::interval)::date - CURRENT_DATE
                            ) <= mst.remind_before_days)
                      THEN 2
                      ELSE 0
                    END
                ) AS color

            FROM rental_vehicle v
            JOIN rental_vehicle_model m ON m.id = v.model_id
            JOIN rental_vehicle_model_maintenance mst ON mst.model_id = m.id   -- интервалы по типам услуг
            JOIN rental_service_type st ON st.id = mst.service_type_id     -- справочник услуг
            LEFT JOIN last_log ll
              ON ll.vehicle_id = v.id
             AND ll.service_type_id = mst.service_type_id
            WHERE v.status != 'inactive';
        """)
