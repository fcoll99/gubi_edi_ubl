# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from odoo.addons.component.core import Component


class EdiPurchaseListenerOutput(Component):
    _name = "edi.purchase.listener.output"
    _inherit = "base.event.listener"
    _apply_on = "purchase.order"

    def _get_backend(self, record):
        return record._get_purchase_order_gubi_ubl_backend()

    def _get_exchange_record_vals(self, record):
        return {"model": record._name, "res_id": record.id}

    def on_generate_purchase_order(self, record):
        backend = self._get_backend(record)
        if not backend:
            return False
        exchange_type = "order_out"
        exchange_record = backend.create_record(
            exchange_type, self._get_exchange_record_vals(record)
        )
        backend.exchange_generate(exchange_record)
        return True
