from odoo.addons.component.core import Component


class EdiProductListenerOutput(Component):
    _name = "edi.product.listener.output"
    _inherit = "base.event.listener"
    _apply_on = "edi.product.catalogue"

    def _get_backend(self, record):
        return record._get_product_backend()

    def _get_exchange_record_vals(self, record):
        return {"model": record._name, "res_id": record.id}

    def on_send_product(self, record):
        backend = self._get_backend(record)
        if not backend:
            return False
        exchange_type = "catalogue_out"
        exchange_record = backend.create_record(
            exchange_type, self._get_exchange_record_vals(record)
        )
        backend.exchange_generate(exchange_record)
        return True
