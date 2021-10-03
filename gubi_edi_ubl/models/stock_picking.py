# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from lxml import etree

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "base.ubl", "edi.exchange.consumer.mixin"]

    def action_done(self):
        res = super(StockPicking, self).action_done()
        self._event("on_done_picking").notify(self)
        return res

    def _get_stock_picking_backend(self):
        partner = self.partner_id.commercial_partner_id
        backend_type = "gubi_ubl"
        if partner.sps_customer_vendor_code and partner.sps_transaction_code:
            backend_type = "sps_ubl"
        backend = self.env["edi.backend"].search(
            [
                ("backend_type_id.code", "=", backend_type),
                "|",
                ("partner_id", "=", partner.id),
                ("partner_id", "=", False),
            ],
            limit=1,
        )
        return backend

    # Generator

    def _ubl_add_header(self, parent_node, ns, origin, version="2.1"):
        now_utc = fields.Datetime.to_string(fields.Datetime.now())
        date = now_utc[:10]
        time = now_utc[11:]
        ubl_version = etree.SubElement(parent_node, ns["cbc"] + "UBLVersionID")
        ubl_version.text = version
        doc_id = etree.SubElement(parent_node, ns["cbc"] + "ID")
        doc_id.text = self.name
        issue_date = etree.SubElement(parent_node, ns["cbc"] + "IssueDate")
        issue_date.text = date
        issue_time = etree.SubElement(parent_node, ns["cbc"] + "IssueTime")
        issue_time.text = time
        purpose_code = etree.SubElement(
            parent_node, ns["cbc"] + "DespatchAdviceTypeCode"
        )
        if self.is_dropship:
            purpose_code.text = "06"
        else:
            purpose_code.text = "00"

        carrier_routing = etree.SubElement(parent_node, ns["cbc"] + "Note")
        if origin.note:
            carrier_routing.text = origin.note
        else:
            carrier_routing.text = ""

    def _ubl_add_order_reference(self, parent_node, ns, origin):
        order_reference = etree.SubElement(parent_node, ns["cac"] + "OrderReference")
        order_id = etree.SubElement(order_reference, ns["cbc"] + "ID")
        if origin.client_order_ref:
            order_id.text = origin.client_order_ref
        date = fields.Date.to_string(origin.sps_order_create_date)
        if date:
            order_date = etree.SubElement(order_reference, ns["cbc"] + "IssueDate")
            order_date.text = date
        if origin.sps_client_order_ref:
            customer_order_id = etree.SubElement(
                order_reference, ns["cbc"] + "CustomerReference"
            )
            customer_order_id.text = origin.sps_client_order_ref

    def _ubl_get_carrier_alpha_code(self, origin):
        if origin.partner_id.vat == "US2036140":
            if self.is_dropship:
                return "DSV"
            else:
                scac = self.name[:3]
                if scac.isalpha():
                    return scac
                else:
                    return "DSV"
        else:
            return "USPG"

    def _ubl_add_additional_reference(self, parent_node, ns, origin):

        bill_of_lading = etree.SubElement(
            parent_node, ns["cac"] + "AdditionalDocumentReference"
        )
        bill_of_lading_id = etree.SubElement(bill_of_lading, ns["cbc"] + "ID")
        date = fields.Datetime.to_string(self.sale_id.date_order)
        bill_of_lading_id.text = self.sale_id.name + "-" + date[:10]
        bill_of_lading_description = etree.SubElement(
            bill_of_lading, ns["cbc"] + "DocumentDescription"
        )
        bill_of_lading_description.text = "BOL"

        carrier_alpha_code = etree.SubElement(
            parent_node, ns["cac"] + "AdditionalDocumentReference"
        )
        carrier_alpha_code_id = etree.SubElement(carrier_alpha_code, ns["cbc"] + "ID")
        # SCAC is the abreviation for "Standard Carrier Alpha Code"
        carrier_alpha_code_id.text = self._ubl_get_carrier_alpha_code(origin)
        carrier_alpha_code_description = etree.SubElement(
            carrier_alpha_code, ns["cbc"] + "DocumentDescription"
        )
        carrier_alpha_code_description.text = "CarrierAlphaCode"

    def _ubl_get_customer_vendor_code(self, customer_rec):
        if customer_rec.sps_customer_vendor_code:
            return customer_rec.sps_customer_vendor_code
        return False

    def _ubl_get_trading_partner_id(self, customer_rec):
        if customer_rec.sps_transaction_code:
            return customer_rec.sps_transaction_code
        return False

    def _ubl_add_parties(self, parent_node, ns, origin):
        supplier_party = etree.SubElement(
            parent_node, ns["cac"] + "DespatchSupplierParty"
        )
        customer_rec = self.env["res.partner"].search(
            [("id", "=", origin.partner_id.id)]
        )
        vendor_code = self._ubl_get_customer_vendor_code(customer_rec)
        if vendor_code:
            vendor_number = etree.SubElement(
                supplier_party, ns["cbc"] + "CustomerAssignedAccountID"
            )
            vendor_number.text = vendor_code
        trading_partner_id = self._ubl_get_trading_partner_id(customer_rec)
        if trading_partner_id:
            trading_partner = etree.SubElement(
                supplier_party, ns["cbc"] + "AdditionalAccountID"
            )
            trading_partner.text = trading_partner_id
        customer = etree.SubElement(parent_node, ns["cac"] + "DeliveryCustomerParty")
        customer_party = etree.SubElement(customer, ns["cac"] + "Party")
        customer_party_name = etree.SubElement(customer_party, ns["cac"] + "PartyName")
        customer_name = etree.SubElement(customer_party_name, ns["cbc"] + "Name")
        customer_name.text = customer_rec.name

    def _ubl_add_delivery(self, parent_node, ns, origin, address_type):
        if address_type == "delivery":
            delivery_partner = self.env["res.partner"].search(
                [("id", "=", origin.partner_shipping_id.id)]
            )
            parent_node = etree.SubElement(parent_node, ns["cac"] + "Delivery")
            ship_date = etree.SubElement(parent_node, ns["cbc"] + "ActualDeliveryDate")
            scheduled_date = fields.Datetime.to_string(self.scheduled_date)
            ship_date.text = scheduled_date[:10]
            delivery_address = "DeliveryAddress"
        else:
            delivery_partner = self.company_id.partner_id
            delivery_address = "OriginAddress"

        self._ubl_add_address(delivery_partner, delivery_address, parent_node, ns)

    def _ubl_get_lading_quantity(self):
        quantity = 0
        for line in self.move_lines:
            quantity += line.quantity_done
        return str(quantity)

    def _ubl_add_shipment(self, parent_node, ns, origin):
        shipment = etree.SubElement(parent_node, ns["cac"] + "Shipment")
        shipment_id = etree.SubElement(shipment, ns["cbc"] + "ID")
        tracking_rec = self.env["stock.picking.tracking"].search(
            [("picking_id", "=", self.id), ("state", "=", "submitted")], limit=1
        )
        shipment_id.text = tracking_rec.tracking_ref or ""
        if origin.partner_id.sps_customer_vendor_code == "10040443":
            # In gubi KG is always used, but in case they use LBS, code sent to sps
            # should be LB, not LBS.
            weight_uom = self.weight_uom_name.upper()
            weight = etree.SubElement(
                shipment, ns["cbc"] + "GrossWeightMeasure", unitCode=weight_uom
            )
            weight.text = str(self.gross_weight)
            # TODO counting done in picking is the way to fill quantity?
            quantity = etree.SubElement(shipment, ns["cbc"] + "ConsignmentQuantity")
            quantity.text = self._ubl_get_lading_quantity()
        # TODO How to check the transportation method?
        transport_means_type = etree.SubElement(shipment, ns["cac"] + "ShipmentStage")
        transport_means_type_code = etree.SubElement(
            transport_means_type, ns["cbc"] + "TransportMeansTypeCode"
        )
        transport_means_type_code.text = origin.sps_transport_method_code or ""
        self._ubl_add_delivery(shipment, ns, origin, "delivery")
        self._ubl_add_delivery(shipment, ns, origin, False)

    def _ubl_add_dispatch_quantity(self, parent_node, ns, line):
        # Only allowed code for sps is EA: Each
        quantity_uom = "EA"
        quantity = etree.SubElement(
            parent_node, ns["cbc"] + "DeliveredQuantity", unitCode=quantity_uom
        )
        quantity.text = str(line.quantity_done)

    def _ubl_add_dispatch_item(self, parent_node, ns, line, order_line):
        item = etree.SubElement(parent_node, ns["cac"] + "Item")
        description = etree.SubElement(item, ns["cbc"] + "Description")
        description.text = line.product_id.name
        customer_item_number = etree.SubElement(
            item, ns["cac"] + "BuyersItemIdentification"
        )
        customer_item_number_id = etree.SubElement(
            customer_item_number, ns["cbc"] + "ID"
        )
        if order_line.product_customer_code:
            customer_item_number_id.text = order_line.product_customer_code
        else:
            customer_item_number_id.text = ""
        item_number = etree.SubElement(item, ns["cac"] + "SellersItemIdentification")
        item_number_id = etree.SubElement(item_number, ns["cbc"] + "ID")
        item_number_id.text = line.product_id.item_number
        # TODO only for DWR bulk orders not dropship
        # TODO if not origin_country_id field, pick the country of the first vendor
        if not self.is_dropship and line.product_id.origin_country_id:
            origin_country = etree.SubElement(parent_node, ns["cac"] + "OriginCountry")
            origin_country_code = etree.SubElement(
                origin_country, ns["cbc"] + "IdentificationCode"
            )
            origin_country_code.text = line.product_id.origin_country_id.code
            origin_country_name = etree.SubElement(origin_country, ns["cbc"] + "Name")
            origin_country_name.text = line.product_id.origin_country_id.name

    def _ubl_get_line_id(self, order_line):
        return str(order_line.sps_sequence)

    def _ubl_add_despatch_line(self, parent_node, ns, line, origin):
        line_root = etree.SubElement(parent_node, ns["cac"] + "DespatchLine")
        # TODO improve implementation of Carrier Assigned package ID
        package_id = etree.SubElement(line_root, ns["cbc"] + "ID")
        if line.product_id.barcode:
            package_id.text = "PACK " + line.product_id.barcode
        else:
            package_id.text = "PACK product_barcode"
        # TODO SSCC ??? (GS1 Serial Shipping Container Code)
        sscc = etree.SubElement(line_root, ns["cbc"] + "UUID")
        sscc.text = "SSCC12345"
        order_line = self._ubl_get_origin_sale_order_line(line, origin)
        if order_line:
            self._ubl_add_dispatch_quantity(line_root, ns, line)
            order_line_reference = etree.SubElement(
                line_root, ns["cac"] + "OrderLineReference"
            )
            line_id = etree.SubElement(order_line_reference, ns["cbc"] + "LineID")
            line_id.text = self._ubl_get_line_id(order_line)
            self._ubl_add_dispatch_item(line_root, ns, line, order_line)

        else:
            raise ValidationError(_("Origin order line not found"))

    def _ubl_get_origin_sale_order(self):
        return self.env["sale.order"].search([("name", "=", self.origin)])

    def _ubl_get_origin_sale_order_line(self, line, origin):
        line = self.env["sale.order.line"].search(
            [("order_id", "=", origin.id), ("product_id", "=", line.product_id.id)]
        )
        return line

    def generate_despatch_advice_ubl_xml_etree(self, version="2.1"):
        nsmap, ns = self._ubl_get_nsmap_namespace("DespatchAdvice-2", version=version)
        xml_root = etree.Element("DespatchAdvice", nsmap=nsmap)
        origin = self._ubl_get_origin_sale_order()
        self._ubl_add_header(xml_root, ns, origin, version)
        self._ubl_add_order_reference(xml_root, ns, origin)
        self._ubl_add_additional_reference(xml_root, ns, origin)
        self._ubl_add_parties(xml_root, ns, origin)
        self._ubl_add_shipment(xml_root, ns, origin)
        for line in self.move_lines:
            self._ubl_add_despatch_line(xml_root, ns, line, origin)
        return xml_root

    def generate_picking_ubl_xml_string(self, version="2.1"):
        self.ensure_one()
        lang = self.get_ubl_lang()
        xml_root = self.with_context(lang=lang).generate_despatch_advice_ubl_xml_etree(
            version=version
        )
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        self._ubl_check_xml_schema(xml_string, "DespatchAdvice", version=version)
        return xml_string

    def get_ubl_lang(self):
        self.ensure_one()
        return self.partner_id.lang or "en_US"
