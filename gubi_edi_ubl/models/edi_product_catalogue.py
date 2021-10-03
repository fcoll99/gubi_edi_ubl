from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import UserError


class EdiProductCatalogue(models.Model):
    _name = "edi.product.catalogue"
    _inherit = ["base.ubl", "edi.exchange.consumer.mixin"]
    _description = "EDI Product Catalogue"

    name = fields.Char("Catalogue Name", required=True, translate=True)
    item_ids = fields.Many2many("product.product", string="Catalogue Items")
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    company_id = fields.Many2one("res.company", "Company", required=True)
    backend_id = fields.Many2one(
        string="EDI backend", comodel_name="edi.backend", ondelete="set null",
    )

    def send_product_button(self):
        self._event("on_send_product").notify(self)

    def _get_product_backend(self):
        partner = self.partner_id.commercial_partner_id
        backend_type = "gubi_ubl"
        exchange_code = "catalogue_out"
        backend = self.env["edi.backend"].search(
            [
                ("backend_type_id.code", "=", backend_type),
                "|",
                ("partner_id", "=", partner.id),
                ("partner_id", "=", False),
            ],
        )
        # It is necessary to set an EDI Backend in the Purchase Exchange Type
        if len(backend) != 1:
            backend_list = backend
            for backend_rec in backend_list:
                exchange_type = self.env["edi.exchange.type"].search(
                    [
                        ("backend_type_id.code", "=", backend_type),
                        ("direction", "=", "output"),
                        ("code", "=", exchange_code),
                        ("backend_id", "=", backend_rec.id),
                    ]
                )
                if exchange_type:
                    backend = backend_rec
            if len(backend) != 1:
                raise UserError(
                    _(
                        "Multiple or no backends detected. "
                        "Check out the EDI configuration"
                    )
                )
        return backend

    def _ubl_get_seller_code_from_product(self, product):
        return product.item_number

    def _ubl_add_provider_party(self, parent_node, ns, version="2.1"):
        self._ubl_add_party(
            self.company_id.partner_id,
            self.company_id,
            "ProviderParty",
            parent_node,
            ns,
            version,
        )

    def _ubl_add_receiver_party(self, parent_node, ns, version="2.1"):
        self._ubl_add_party(
            self.partner_id, False, "ReceiverParty", parent_node, ns, version
        )

    def _ubl_add_item_comparison(self, product, parent_node, ns, version="2.1"):
        item_comp_root = etree.SubElement(parent_node, ns["cac"] + "ItemComparison")
        price_amount = etree.SubElement(
            item_comp_root, ns["cbc"] + "PriceAmount", currencyID="USD"
        )
        price_amount.text = str(product.lst_price)

    def _ubl_add_item(
        self,
        name,
        product,
        parent_node,
        ns,
        type_="purchase",
        seller=False,
        customer=False,
        version="2.1",
    ):
        """Beware that product may be False (in particular on invoices)"""
        assert type_ in ("sale", "purchase"), "Wrong type param"
        assert name, "name is a required arg"
        item = etree.SubElement(parent_node, ns["cac"] + "Item")
        product_name = False
        seller_code = False
        if product:
            if type_ == "purchase":
                if seller:
                    sellers = product._select_seller(
                        partner_id=seller, quantity=0.0, date=None, uom_id=False
                    )
                    if sellers:
                        product_name = sellers[0].product_name
                        seller_code = sellers[0].product_code
            if not seller_code:
                seller_code = self._ubl_get_seller_code_from_product(product)
            if not product_name:
                variant = ", ".join(product.attribute_line_ids.mapped("value_ids.name"))
                product_name = (
                    variant and "{} ({})".format(product.name, variant) or product.name
                )
        description = etree.SubElement(item, ns["cbc"] + "Description")
        description.text = name
        name_node = etree.SubElement(item, ns["cbc"] + "Name")
        name_node.text = product_name or name.split("\n")[0]

        customer_code = self._ubl_get_customer_product_code(product, customer)
        if customer_code:
            buyer_identification = etree.SubElement(
                item, ns["cac"] + "BuyersItemIdentification"
            )
            buyer_identification_id = etree.SubElement(
                buyer_identification, ns["cbc"] + "ID"
            )
            buyer_identification_id.text = customer_code
        if seller_code:
            seller_identification = etree.SubElement(
                item, ns["cac"] + "SellersItemIdentification"
            )
            seller_identification_id = etree.SubElement(
                seller_identification, ns["cbc"] + "ID"
            )
            seller_identification_id.text = seller_code
        if product:
            if product.barcode:
                std_identification = etree.SubElement(
                    item, ns["cac"] + "StandardItemIdentification"
                )
                std_identification_id = etree.SubElement(
                    std_identification,
                    ns["cbc"] + "ID",
                    schemeAgencyID="6",
                    schemeID="GTIN",
                )
                std_identification_id.text = product.barcode

            for attribute_value in product.attribute_line_ids.mapped("value_ids"):
                item_property = etree.SubElement(
                    item, ns["cac"] + "AdditionalItemProperty"
                )
                property_name = etree.SubElement(item_property, ns["cbc"] + "Name")
                property_name.text = attribute_value.attribute_id.name
                property_value = etree.SubElement(item_property, ns["cbc"] + "Value")
                property_value.text = attribute_value.name

    def _ubl_add_item_property(self, name, value, parent_node, ns):
        item = etree.SubElement(parent_node, ns["cac"] + "KeywordItemProperty")
        valueQuantity = etree.SubElement(item, ns["cbc"] + "Name")
        valueQuantity.text = name
        valueQualifier = etree.SubElement(item, ns["cbc"] + "Value")
        valueQualifier.text = value

    def _ubl_add_product_data(self, product, parent_node, ns):
        collection_str = self.env["product.product"]._fields["x_Collection"].string
        if collection_str and product.x_Collection.name:
            self._ubl_add_item_property(
                collection_str, product.x_Collection.name, parent_node, ns
            )
        designed_by_str = self.env["product.product"]._fields["x_Designed_by"].string
        if designed_by_str and product.x_Designed_by.name:
            self._ubl_add_item_property(
                designed_by_str, product.x_Designed_by.name, parent_node, ns
            )
        designed_in_str = self.env["product.product"]._fields["designed_in"].string
        if designed_in_str and product.designed_in:
            self._ubl_add_item_property(
                designed_in_str, product.designed_in, parent_node, ns
            )

    def _ubl_add_catalogue_line(self, product, catalogue_line_id, parent_node, ns):
        line_root = etree.SubElement(parent_node, ns["cac"] + "CatalogueLine")
        catalogue_id = etree.SubElement(line_root, ns["cbc"] + "ID")
        catalogue_id.text = str(catalogue_line_id)
        self._ubl_add_item_comparison(product, line_root, ns)
        self._ubl_add_item(
            product.name,
            product,
            line_root,
            ns,
            type_="purchase",
            seller=self.company_id.partner_id,
            customer=self.partner_id,
            version="2.1",
        )
        self._ubl_add_product_data(product, line_root, ns)

    def _ubl_add_header(self, parent_node, ns, version="2.1"):
        now_utc = fields.Datetime.to_string(fields.Datetime.now())
        date = now_utc[:10]
        ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
        ubl_version.text = version
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = date

    def generate_product_ubl_xml_etree(self, version="2.1"):
        nsmap, ns = self._ubl_get_nsmap_namespace("Catalogue-2", version=version)
        xml_root = etree.Element("Catalogue", nsmap=nsmap)
        self._ubl_add_header(xml_root, ns, version=version)
        self._ubl_add_provider_party(xml_root, ns)
        self._ubl_add_receiver_party(xml_root, ns)

        catalogue_line_id = 0
        for product in self.item_ids:
            catalogue_line_id = catalogue_line_id + 1
            self._ubl_add_catalogue_line(product, catalogue_line_id, xml_root, ns)

        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        self._ubl_check_xml_schema(xml_string, "Catalogue", version=version)
        xml_string.decode("utf-8")
        return xml_string
