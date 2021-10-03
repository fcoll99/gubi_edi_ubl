# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderImport(models.TransientModel):
    _name = "sale.order.import"
    _inherit = ["sale.order.import", "base.ubl"]

    @api.model
    def parse_xml_order(self, xml_root, detect_doc_type=False):
        start_tag = "{urn:oasis:names:specification:ubl:schema:xsd:"
        rfq = "RequestForQuotation"
        if xml_root.tag == start_tag + "Order-2}Order":
            if detect_doc_type:
                return "order"
            else:
                return self.parse_ubl_sale_order(xml_root)
        elif xml_root.tag == "{}{}-2}}{}".format(start_tag, rfq, rfq):
            if detect_doc_type:
                return "rfq"
            else:
                return self.parse_ubl_sale_order(xml_root)
        else:
            # TODO: this!
            raise ValidationError(_("Sad story"))
            # return super(SaleOrderImport, self).parse_xml_order(xml_root)

    def parse_ubl_sale_order_line(self, line, ns):
        # qty_prec = self.env["decimal.precision"].precision_get("Product UoS")
        line_item = line.xpath("cac:LineItem", namespaces=ns)[0]
        # line_id_xpath = line_item.xpath('cbc:ID', namespaces=ns)
        # line_id = line_id_xpath[0].text
        qty_xpath = line_item.xpath("cbc:Quantity", namespaces=ns)
        qty = float(qty_xpath[0].text)
        price_unit = 0.0
        subtotal_without_tax_xpath = line_item.xpath(
            "cbc:LineExtensionAmount", namespaces=ns
        )
        price_xpath = line_item.xpath("cac:Price/cbc:PriceAmount", namespaces=ns)
        if price_xpath:
            price_unit = float(price_xpath[0].text)

        res_line = {
            "product": self.ubl_parse_product(line_item, ns),
            "qty": qty,
            "uom": {"unece_code": qty_xpath[0].attrib.get("unitCode")},
            "price_unit": price_unit,
            "currency_id": price_xpath[0].attrib.get("currencyID"),
            "line_amount_without_tax": subtotal_without_tax_xpath
            and subtotal_without_tax_xpath[0].text
            or False,
        }
        return res_line

    def _parse_header_data(self, xml_root, root_name, ns):
        purchase_order_xpath = xml_root.xpath("/%s/cbc:ID" % root_name, namespaces=ns)
        date_xpath = xml_root.xpath("/%s/cbc:IssueDate" % root_name, namespaces=ns)
        order_type_code_xpath = xml_root.xpath(
            "/%s/cbc:OrderTypeCode" % root_name, namespaces=ns
        )
        customer_ref_xpath = xml_root.xpath(
            "/%s/cbc:CustomerReference" % root_name, namespaces=ns
        )
        cancel_date_xpath = xml_root.xpath(
            "/%s/cac:ValidityPeriod/cbc:EndDate" % root_name, namespaces=ns
        )
        header_data = {
            "id": purchase_order_xpath and purchase_order_xpath[0].text or False,
            "code": order_type_code_xpath and order_type_code_xpath[0].text or False,
            "date": date_xpath and date_xpath[0].text or False,
            "customer_order_ref": customer_ref_xpath
            and customer_ref_xpath[0].text
            or False,
            "cancel_date": cancel_date_xpath and cancel_date_xpath[0].text or False,
        }
        return header_data

    def _parse_transaction_conditions(self, xml_root, root_name, ns):
        order_terms_xpath = xml_root.xpath(
            "/%s/cac:TransactionConditions/cbc:Description" % root_name, namespaces=ns
        )
        order_terms = {
            "order_terms": order_terms_xpath and order_terms_xpath[0].text or False,
        }
        return order_terms

    def _parse_billing_party(self, xml_root, root_name, ns):

        bill_to_delivery_phone_xpath = xml_root.xpath(
            "/%s/cac:AccountingCustomerParty/cac:DeliveryContact/cbc:Telephone"
            % root_name,
            namespaces=ns,
        )
        bill_to_delivery_mail_xpath = xml_root.xpath(
            "/%s/cac:AccountingCustomerParty/cac:DeliveryContact/cbc:ElectronicMail"
            % root_name,
            namespaces=ns,
        )
        bill_to_buyer_phone_xpath = xml_root.xpath(
            "/%s/cac:AccountingCustomerParty/cac:BuyerContact/cbc:Telephone"
            % root_name,
            namespaces=ns,
        )
        bill_to_buyer_mail_xpath = xml_root.xpath(
            "/%s/cac:AccountingCustomerParty/cac:BuyerContact/cbc:ElectronicMail"
            % root_name,
            namespaces=ns,
        )

        buyer_contact = xml_root.xpath(
            "/%s/cac:BuyerCustomerParty/cac:BuyerContact/cbc:Name" % root_name,
            namespaces=ns,
        )
        name_xpath = xml_root.xpath(
            "/%s/cac:BuyerCustomerParty/cac:Party/cac:PartyName/cbc:Name" % root_name,
            namespaces=ns,
        )
        billing_party = {
            "name": name_xpath and name_xpath[0].text or False,
            "contact_name": buyer_contact and buyer_contact[0].text or False,
        }

        if bill_to_delivery_mail_xpath:
            billing_party["contact_phone"] = (
                bill_to_delivery_phone_xpath and bill_to_delivery_mail_xpath[0].text
            )
            billing_party["contact_mail"] = (
                bill_to_delivery_mail_xpath and bill_to_delivery_mail_xpath[0].text
            )
        else:
            billing_party["contact_phone"] = (
                bill_to_buyer_phone_xpath and bill_to_buyer_mail_xpath[0].text or False
            )
            billing_party["contact_mail"] = (
                bill_to_buyer_mail_xpath and bill_to_buyer_mail_xpath[0].text or False
            )
        # TODO: need to parse the billing address
        return billing_party

    def _parse_delivery_data(self, xml_root, root_name, ns):
        # Delivery related dates
        earliest_ship_date_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:PromisedDeliveryPeriod/cbc:StartDate" % root_name,
            namespaces=ns,
        )
        latest_ship_date_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:PromisedDeliveryPeriod/cbc:EndDate" % root_name,
            namespaces=ns,
        )
        requested_start_ship_date_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:RequestedDeliveryPeriod/cbc:StartDate" % root_name,
            namespaces=ns,
        )
        requested_end_ship_date_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:RequestedDeliveryPeriod/cbc:EndDate" % root_name,
            namespaces=ns,
        )
        # Delivery carrier data
        carrier_type_code_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:Shipment/cac:ShipmentStage/cbc:TransportModeCode"
            % root_name,
            namespaces=ns,
        )
        carrier_routing_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:Shipment/cbc:Information" % root_name, namespaces=ns,
        )
        carrier_service_level_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:Shipment/cbc:HandlingCode" % root_name, namespaces=ns,
        )
        delivery_quantity_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cbc:Quantity" % root_name, namespaces=ns
        )
        delivery_terms_xpath = xml_root.xpath(
            "/%s/cac:DeliveryTerms/cbc:ID" % root_name, namespaces=ns
        )
        delivery_data = {
            "earliest_ship_date": earliest_ship_date_xpath
            and earliest_ship_date_xpath[0].text
            or False,
            "latest_ship_date": latest_ship_date_xpath
            and latest_ship_date_xpath[0].text
            or False,
            "requested_start_ship_date": requested_start_ship_date_xpath
            and requested_start_ship_date_xpath[0].text
            or False,
            "requested_end_ship_date": requested_end_ship_date_xpath
            and requested_end_ship_date_xpath[0].text
            or False,
            "carrier_type_code": carrier_type_code_xpath
            and carrier_type_code_xpath[0].text
            or False,
            "carrier_routing": carrier_routing_xpath
            and carrier_routing_xpath[0].text
            or False,
            "carrier_service_level_code": carrier_service_level_xpath
            and carrier_service_level_xpath[0].text
            or False,
            "delivery_quantity": delivery_quantity_xpath
            and delivery_quantity_xpath[0].text
            or False,
            "delivery_terms": delivery_terms_xpath
            and delivery_terms_xpath[0].text
            or False,
        }
        return delivery_data

    def _parse_currency(self, xml_root, root_name, ns):
        currency_code = False
        for cur_node_name in ("DocumentCurrencyCode", "PricingCurrencyCode"):
            currency_xpath = xml_root.xpath(
                "/{}/cbc:{}".format(root_name, cur_node_name), namespaces=ns
            )
            if currency_xpath:
                currency_code = currency_xpath[0].text
                break

        if not currency_code:
            currency_xpath = xml_root.xpath("//cbc:LineExtensionAmount", namespaces=ns)
            if currency_xpath:
                currency_code = currency_xpath[0].attrib.get("currencyID")

        return currency_code

    def _parse_supplier_party(self, xml_root, root_name, ns):
        party_node = xml_root.xpath(
            "/%s/cac:SellerSupplierParty" % root_name, namespaces=ns
        )
        supplier_party = self.ubl_parse_supplier_party(party_node[0], ns)

        sps_id_xpath = xml_root.xpath(
            "/%s/cac:SellerSupplierParty/cbc:AdditionalAccountID" % root_name,
            namespaces=ns,
        )
        supplier_party["sps_id"] = sps_id_xpath and sps_id_xpath[0].text or False

        return supplier_party

    def _parse_customer_party(self, xml_root, root_name, ns):
        party_node = xml_root.xpath(
            "/%s/cac:BuyerCustomerParty" % root_name, namespaces=ns
        )
        customer_party = self.ubl_parse_customer_party(party_node[0], ns)

        billing_acc_xpath = xml_root.xpath(
            "/%s/cac:BuyerCustomerParty/cac:Party/cac:FinancialAccount/cbc:ID"
            % root_name,
            namespaces=ns,
        )
        division_xpath = xml_root.xpath(
            "/%s/cac:BuyerCustomerParty/cac:Party/cac:FinancialAccount"
            "/cac:FinancialInstitutionBranch/ID" % root_name,
            namespaces=ns,
        )
        customer_party["billing_account"] = (
            billing_acc_xpath and billing_acc_xpath[0].text or False,
        )
        customer_party["division"] = (
            division_xpath and division_xpath[0].text or False,
        )
        return customer_party

    def _parse_delivery_address(self, xml_root, root_name, ns):
        delivery_xpath = xml_root.xpath("/%s/cac:Delivery" % root_name, namespaces=ns)
        delivery_address = self.ubl_parse_delivery(delivery_xpath[0], ns)
        delivery_building_xpath = xml_root.xpath(
            "/%s/cac:Delivery/cac:DeliveryAddress/cbc:BuildingName" % root_name,
            namespaces=ns,
        )
        if not delivery_address["street"]:
            delivery_address_line_xpath = xml_root.xpath(
                "/%s/cac:Delivery/cac:DeliveryAddress/cac:AddressLine/cbc:Line"
                % root_name,
                namespaces=ns,
            )
            delivery_address["street"] = (
                delivery_address_line_xpath
                and delivery_address_line_xpath[0].text
                or False
            )

        delivery_address["building_name"] = (
            delivery_building_xpath and delivery_building_xpath[0].text or False
        )
        return delivery_address

    def _parse_order_lines(self, xml_root, root_name, line_name, ns):
        lines_xpath = xml_root.xpath(
            "/{}/{}".format(root_name, line_name), namespaces=ns
        )
        product_sequence_id_xpath = xml_root.xpath(
            "/{}/{}/cac:LineItem/cbc:ID".format(root_name, line_name), namespaces=ns
        )
        line_requested_date_xpath = xml_root.xpath(
            "/{}/{}/cac:LineItem/cac:Delivery/{}/cbc:StartDate".format(
                root_name, line_name, "cac:RequestedDeliveryPeriod",
            ),
            namespaces=ns,
        )
        item_description_xpath = xml_root.xpath(
            "/{}/{}/cac:LineItem/cac:Item/cbc:Description".format(root_name, line_name),
            namespaces=ns,
        )
        item_name_xpath = xml_root.xpath(
            "/{}/{}/cac:LineItem/cac:Item/cbc:Name".format(root_name, line_name),
            namespaces=ns,
        )
        item_customer_ref_xpath = xml_root.xpath(
            "/{}/{}/cac:LineItem/cac:Item/cac:BuyersItemIdentification/cbc:ID".format(
                root_name, line_name
            ),
            namespaces=ns,
        )

        item_base_quantity_xpath = xml_root.xpath(
            "/{}/{}/cac:LineItem/cac:Price/cbc:BaseQuantity".format(
                root_name, line_name
            ),
            namespaces=ns,
        )

        line_num = 0
        res_lines = []
        for line in lines_xpath:
            line_dict = self.parse_ubl_sale_order_line(line, ns)
            line_dict["product"].pop("barcode", None)

            if not item_description_xpath[line_num].text:
                line_dict["product"]["name"] = item_name_xpath[line_num].text
            else:
                line_dict["product"]["name"] = item_description_xpath[line_num].text

            line_dict["product"]["sequence_id"] = product_sequence_id_xpath[
                line_num
            ].text
            if len(line_requested_date_xpath) > line_num:
                line_dict["requested_ship_date"] = line_requested_date_xpath[
                    line_num
                ].text
            if len(item_customer_ref_xpath) > line_num:
                line_dict["product"]["customer_ref"] = item_customer_ref_xpath[
                    line_num
                ].text
            if len(item_base_quantity_xpath) > line_num:
                line_dict["base_qty"] = item_base_quantity_xpath[line_num].text

            res_lines.append(line_dict)
            line_num += 1

        return res_lines

    def _parse_notes(self, xml_root, root_name, ns):
        notes = []
        notes_xpath = xml_root.xpath("/%s/cbc:Note" % root_name, namespaces=ns)
        for note in notes_xpath:
            note_text = note.text
            notes.append(note_text)

        return notes

    def _create_supplier_info_if_missing(self, product, partner, code):
        supplierinfo = product._select_customerinfo(partner=partner)
        if not supplierinfo:
            self.env["product.customerinfo"].create(
                {
                    "name": partner.id,
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "product_id": product.id,
                    "product_code": code,
                    "min_qty": 1.0,
                    "price": 0,
                }
            )
        return True

    def _create_sale_order_ubl(self, ubl_content):
        # TODO: check if VAT exists, and if not search by sps_customer_vendor_code
        if ubl_content["customer_partner"]["vat"]:
            customer = self.env["res.partner"].search(
                [
                    ("vat", "=", ubl_content["customer_partner"]["vat"],),
                    ("parent_id", "=", False),
                ]
            )
        else:
            customer = self.env["res.partner"].search(
                [
                    (
                        "sps_customer_vendor_code",
                        "=",
                        ubl_content["customer_partner"]["ref"],
                    )
                ]
            )
        if not customer:
            raise ValidationError(_("Customer code not found"))

        order_header = ubl_content["purchase_order_header"]
        customer_ref = order_header["id"]

        addr = customer.address_get(["invoice", "delivery"])

        if ubl_content["currency"]["iso"]:
            currency_name = ubl_content["currency"]["iso"]
            currency = self.env["res.currency"].search([("name", "=", currency_name)])
        else:
            currency = False

        # TODO: better way to find address?
        delivery_address = ubl_content["delivery_address"]["street"]
        delivery_address_id = (
            self.env["res.partner"]
            .search(
                [
                    ("parent_id", "=", customer.id),
                    ("street", "=", delivery_address),
                    ("type", "=", "delivery"),
                ]
            )
            .id
        )
        if not delivery_address_id:
            # TODO: evaluate the creation of the address if missing.
            delivery_address_id = addr["delivery"]

        incoterms = ubl_content["delivery_data"]["delivery_terms"]
        incoterms_id = (
            self.env["account.incoterms"].search([("code", "=", incoterms)]).id
        )

        payment_terms = ubl_content["order_terms"]
        # TODO: add a standard coding to identify payment terms?
        payment_terms_id = (
            self.env["account.payment.term"]
            .search([("name", "ilike", payment_terms["order_terms"])], limit=1,)
            .id
        )
        if not customer.sps_transaction_code:
            customer.write(
                {"sps_transaction_code": ubl_content["supplier_partner"]["sps_id"]}
            )

        now_utc = fields.Datetime.to_string(fields.Datetime.now())
        time = " " + now_utc[11:]
        res = {
            "partner_id": customer.id,
            "state": "draft",
            "date_order": order_header.get("date") + time,
            "client_order_ref": customer_ref,
            "sps_client_order_ref": order_header.get("customer_order_ref"),
            "partner_shipping_id": delivery_address_id,
            "partner_invoice_id": addr["invoice"],
            "order_placed_by": ubl_content["billing_partner"]["contact_name"] or False,
            "incoterm": incoterms_id,
            "payment_term_id": payment_terms_id,
            "sps_order_create_date": order_header.get("date"),
            "note": ubl_content["delivery_data"]["carrier_routing"] or False,
        }

        if currency:
            res["currency_id"] = currency.id

        if order_header["cancel_date"]:
            res["validity_date"] = order_header.get("cancel_date")

        if ubl_content["delivery_data"]["requested_start_ship_date"]:
            res["commitment_date"] = ubl_content["delivery_data"][
                "requested_start_ship_date"
            ]

        if ubl_content["delivery_data"]["carrier_type_code"]:
            res["sps_transport_method_code"] = ubl_content["delivery_data"][
                "carrier_type_code"
            ]

        quotation_rec = self.env["sale.order"].create(res)
        sol_model = self.env["sale.order.line"]
        order_lines = ubl_content["lines"]
        for line in order_lines:
            sequence = line["product"]["sequence_id"]
            product_no = line["product"]["code"]
            product_no = product_no.split(" ")[0]
            product = self.env["product.product"].search(
                [("item_number", "=", product_no)]
            )
            if not product:
                raise ValidationError(
                    _("Product code not found (%s). Line %s") % (product_no, sequence)
                )
            # TODO: how to consider discounts? Done manually by Gubi.
            # TODO: taxes!
            vals = {
                "name": sol_model.get_sale_order_line_multiline_description_sale(
                    product
                ),
                "product_id": product.id,
                "product_uom_qty": line["qty"],
                "price_unit": line["price_unit"],
                "sps_sequence": sequence,
                "order_id": quotation_rec.id,
            }

            self._create_supplier_info_if_missing(
                product, customer, line["product"]["customer_ref"]
            )

            sol_model.create(vals)
        return quotation_rec

    def parse_ubl_sale_order(self, xml_root):
        ns = xml_root.nsmap
        main_xmlns = ns.pop(None)
        ns["main"] = main_xmlns
        document = "Order"
        root_name = "main:Order"
        line_name = "cac:OrderLine"
        doc_type = "order"
        # Validate content according to xsd file
        xml_string = etree.tostring(
            xml_root, pretty_print=True, encoding="UTF-8", xml_declaration=True
        )
        self._ubl_check_xml_schema(
            xml_string, document, version=self._ubl_get_version(xml_root, root_name, ns)
        )

        # --------------------------- Parse content --------------------------- #

        # Purchase Order IDs
        header_data = self._parse_header_data(xml_root, root_name, ns)

        # Order terms
        order_terms = self._parse_transaction_conditions(xml_root, root_name, ns)

        # Document Currency
        currency_code = self._parse_currency(xml_root, root_name, ns)

        # Delivery
        delivery_data = self._parse_delivery_data(xml_root, root_name, ns)
        delivery_address = self._parse_delivery_address(xml_root, root_name, ns)

        # Supplier party
        supplier_party = self._parse_supplier_party(xml_root, root_name, ns)

        # Customer party
        customer_party = self._parse_customer_party(xml_root, root_name, ns)

        # Billing party
        billing_party = self._parse_billing_party(xml_root, root_name, ns)

        # Notes
        notes = self._parse_notes(xml_root, root_name, ns)

        # Order lines
        res_lines = self._parse_order_lines(xml_root, root_name, line_name, ns)

        ubl_content = {
            "purchase_order_header": header_data,
            "billing_partner": billing_party,
            "delivery_data": delivery_data,
            "delivery_address": delivery_address,
            "currency": {"iso": currency_code},
            "supplier_partner": supplier_party,
            "customer_partner": customer_party,
            "note": notes,
            "lines": res_lines,
            "doc_type": doc_type,
            "order_terms": order_terms,
        }

        so = self._create_sale_order_ubl(ubl_content)
        return so
