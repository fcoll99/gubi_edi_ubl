from odoo.addons.component.core import Component


class EdiPickingListenerOutput(Component):
    _name = "edi.picking.listener.output"
    _inherit = "base.event.listener"
    _apply_on = "stock.picking"

    def _get_picking_backend(self, record):
        return record._get_stock_picking_backend()

    def _get_backend(self, record):
        return self._get_picking_backend(record)

    def _get_exchange_record_vals(self, record):
        return {"model": record._name, "res_id": record.id}

    def on_done_picking(self, record):
        backend = self._get_backend(record)
        if not backend:
            return False
        exchange_type = "picking_out"
        exchange_record = backend.create_record(
            exchange_type, self._get_exchange_record_vals(record)
        )
        backend.exchange_generate(exchange_record)
        return True
