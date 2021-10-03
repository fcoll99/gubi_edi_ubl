from odoo.addons.component.core import Component


class EdiProductGenerate(Component):
    _name = "edi.output.generate.product.ubl"
    _inherit = "edi.component.output.mixin"
    _description = "Generates product catalogues in edi format"
    _usage = "output.generate"
    _backend_type = "gubi_ubl"
    _exchange_type = "catalogue_out"

    def generate(self):
        return self.generate_product_data()

    def generate_product_data(self):
        product_bytes = self.exchange_record.record.generate_product_ubl_xml_etree()
        return product_bytes
