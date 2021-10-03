# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from odoo.addons.component.core import Component


class EdiInvoiceListenerOutput(Component):
    _name = "edi.invoice.listener.output"
    _inherit = "base.event.listener"
    _apply_on = "account.move"

    def _get_backend(self, record):
        return record._get_account_move_gubi_ubl_backend()

    def _get_exchange_record_vals(self, record):
        return {"model": record._name, "res_id": record.id}

    def on_post_account_move(self, record):
        backend = self._get_backend(record)
        if not backend:
            return False
        exchange_type = "invoice_out"
        if record.type == "out_invoice":
            exchange_record = backend.create_record(
                exchange_type, self._get_exchange_record_vals(record)
            )
            backend.exchange_generate(exchange_record)
        return True
