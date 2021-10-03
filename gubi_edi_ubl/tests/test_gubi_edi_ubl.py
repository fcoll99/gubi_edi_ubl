# Copyright 2021 ForgeFlow, S.L.
# License OPL-1

import datetime

from lxml import etree

from odoo import fields
from odoo.modules.module import get_module_resource

from odoo.addons.edi.tests.common import EDIBackendCommonComponentTestCase


class TestGubiEdiUbl(EDIBackendCommonComponentTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        # cls.journal_model = cls.env["account.journal"]
        cls.company_model = cls.env["res.company"]
        cls.partner_model = cls.env["res.partner"]
        cls.payment_terms_model = cls.env["account.payment.term"]
        cls.product_model = cls.env["product.product"]
        cls.account_model = cls.env["account.account"]
        cls.so_model = cls.env["sale.order"]
        cls.am_model = cls.env["account.move"]
        cls.aml_model = cls.env["account.move.line"]
        cls.customerinfo_model = cls.env["product.customerinfo"]
        cls.prcat = cls.env["edi.product.catalogue"]
        cls.attr = cls.env["product.attribute"]
        cls.prod_attr_val = cls.env["product.attribute.value"]
        cls.edi_backend_model = cls.env["edi.backend"]
        cls.exchange_model = cls.env["edi.exchange.record"]
        cls.backend_type_gubi_ubl = cls.env.ref(
            "gubi_edi_ubl.gubi_edi_backend_type_ubl"
        )
        cls.backend_type_sps_ubl = cls.env.ref("gubi_edi_ubl.gubi_edi_backend_type_sps")
        cls.type_ubl_invoice_out = cls.env.ref(
            "gubi_edi_ubl.gubi_edi_exchange_type_ubl_invoice_out"
        )
        cls.type_sps_picking_out = cls.env.ref(
            "gubi_edi_ubl.gubi_edi_exchange_type_sps_picking_out"
        )
        cls.type_ubl_catalogue_out = cls.env.ref(
            "gubi_edi_ubl.gubi_edi_exchange_type_ubl_catalogue_out"
        )
        # Assign a UNECE categ and type to all taxes:
        cls.std_unece = cls.env.ref("account_tax_unece.tax_categ_s")
        cls.type_vat_unece = cls.env.ref("account_tax_unece.tax_type_vat")
        cls.env["account.tax"].search([]).write(
            {
                "unece_categ_id": cls.std_unece.id,
                "unece_type_id": cls.type_vat_unece.id,
            }
        )

        cls.gubi_as = cls.env.ref("base.main_company")
        cls.gubi_as.name = "Gubi A/S"
        cls.gubi_as.partner_id.vat = "DK12345678"

        cls.gubi_design = cls.company_model.create({"name": "Gubi Design Inc."})
        cls.gubi_pty = cls.company_model.create({"name": "Gubi Pty. Ltd."})
        cls.gubi_retail = cls.company_model.create({"name": "Gubi Retail ApS"})

        cls.ydesign = cls.partner_model.create(
            {
                "name": "YDesign",
                "sps_customer_vendor_code": "3372967",
                "sps_transaction_code": "CITALLGUBILININ",
                "vat": "US300500199",
            }
        )
        cls.ydesign_shipping = cls.partner_model.create(
            {
                "name": "YDesign Warehouse",
                "street": "5201 Hampden Lane",
                "type": "delivery",
                "parent_id": cls.ydesign.id,
            }
        )
        cls.ydesign_invoice = cls.partner_model.create(
            {
                "name": "YDesign Bills",
                "street": "Avon Way",
                "type": "invoice",
                "parent_id": cls.ydesign.id,
            }
        )
        cls.dwr = cls.partner_model.create(
            {
                "name": "DWR",
                "sps_customer_vendor_code": "10040443",
                "vat": "US2036140",
                "city": "Stamford",
                "zip": "06902",
                "state_id": cls.env["res.country.state"]
                .search([("name", "=", "Connecticut")])
                .id,
                "country_id": cls.env["res.country"]
                .search([("name", "=", "United States")])
                .id,
                "sps_transaction_code": "FRQALLGUBILININ",
            }
        )
        cls.dwr_shipping = cls.partner_model.create(
            {
                "name": "DWR Warehouse",
                "street": "3001 Afton Drive",
                "city": "Batavia",
                "zip": "45103",
                "state_id": cls.env["res.country.state"]
                .search([("name", "=", "Connecticut")])
                .id,
                "country_id": cls.env["res.country"]
                .search([("name", "=", "United States")])
                .id,
                "type": "delivery",
                "parent_id": cls.dwr.id,
            }
        )
        cls.dwr_invoice = cls.partner_model.create(
            {
                "name": "DWR Bills",
                "street": "Avon Way",
                "city": "Stamford",
                "zip": "06902",
                "state_id": cls.env["res.country.state"]
                .search([("name", "=", "Connecticut")])
                .id,
                "country_id": cls.env["res.country"]
                .search([("name", "=", "United States")])
                .id,
                "type": "invoice",
                "parent_id": cls.dwr.id,
            }
        )
        cls.net_60_terms = cls.payment_terms_model.create({"name": "Net 60 days"})
        cls.net_30_terms = cls.payment_terms_model.create({"name": "Net 30 days"})
        cls.customer_1 = cls.partner_model.create(
            {
                "name": "Test customer 1",
                "vat": "DK12345674",
                "sps_customer_vendor_code": "1234567",
            }
        )
        cls.cust_1_backend = cls.edi_backend_model.create(
            {
                "name": "EDI Backend for customer 1",
                "backend_type_id": cls.backend_type_gubi_ubl.id,
                "partner_id": cls.customer_1.id,
            }
        )
        cls.ydesign_backend = cls.edi_backend_model.create(
            {
                "name": "EDI Backend for YDesign",
                "backend_type_id": cls.backend_type_gubi_ubl.id,
                "partner_id": cls.ydesign.id,
            }
        )
        cls.dwr_backend = cls.edi_backend_model.create(
            {
                "name": "EDI Backend for DWR",
                "backend_type_id": cls.backend_type_sps_ubl.id,
                "partner_id": cls.dwr.id,
            }
        )
        cls.invoice_backend = cls.env.ref("gubi_edi_ubl.gubi_edi_backend_sps_invoice")
        cls.catalogue_backend = cls.env.ref(
            "gubi_edi_ubl.gubi_edi_backend_sps_catalogue"
        )

        # attributes
        cls.attribute_1 = cls._create_attribute("x_collection", "no_variant", "radio")
        cls.attribute_2 = cls._create_attribute("x_designed_by", "no_variant", "radio")
        # product attribute values
        cls.prod_attr_val_1 = cls.prod_attr_val.create(
            {"name": "x_collection", "attribute_id": cls.attribute_1.id}
        )
        cls.prod_attr_val_2 = cls.prod_attr_val.create(
            {"name": "x_designed_by", "attribute_id": cls.attribute_2.id}
        )

        # products:
        cls.product_1 = cls._create_product("10055887", 100.0)
        cls.product_2 = cls._create_product("10000123")
        cls.product_3 = cls._create_product("10010976")
        cls.product_4 = cls._create_product("10000040")
        cls.product_5 = cls._create_product("10000041")
        cls.product_6 = cls._create_product("10000042")
        cls.product_7 = cls._create_product("10000043")
        cls.product_8 = cls._create_product("10092371 NF079/1582")
        cls.product_9 = cls._create_product("10092372 NF079/1657")
        cls.product_10 = cls._create_product("10092373 NF079/2086")

        cls.customerinfo_1 = cls._create_partnerinfo(
            cls.ydesign, cls.product_2, "GUBY0000001", 100.0
        )
        cls.customerinfo_2 = cls._create_partnerinfo(
            cls.customer_1, cls.product_2, "GUBY0000002", 50.0
        )

        cls.today = fields.Datetime.today()

        # Sales Order:
        cls.so_1 = cls.so_model.create(
            {
                "partner_id": cls.customer_1.id,
                "currency_id": cls.env["res.currency"]
                .search([("name", "=", "EUR")])
                .id,
                "amount_untaxed": 750.0,
                "amount_total": 750.0,
                "sps_order_create_date": cls.today,
                "sps_client_order_ref": "L1368872",
                "client_order_ref": "POSO1TEST",
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product_2.name,
                            "product_id": cls.product_2.id,
                            "product_uom_qty": 10.0,
                            "product_uom": cls.product_2.uom_id.id,
                            "price_unit": 2,
                            "tax_id": False,
                            "sps_sequence": 1,
                        },
                    )
                ],
            }
        )
        cls.so_1.action_confirm()

        cls.so_3 = cls.so_model.create(
            {
                "partner_id": cls.dwr.id,
                "currency_id": cls.env["res.currency"]
                .search([("name", "=", "USD")])
                .id,
                "client_order_ref": "PO9341050",
                "sps_order_create_date": datetime.datetime.strptime(
                    "2021-07-16", "%Y-%m-%d"
                ),
                "sps_transport_method_code": "O",
                "note": "Ocean",
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product_8.name,
                            "product_id": cls.product_8.id,
                            "product_uom_qty": 21.0,
                            "product_uom": cls.product_8.uom_id.id,
                            "price_unit": 245.85,
                            "tax_id": False,
                            "sps_sequence": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": cls.product_9.name,
                            "product_id": cls.product_9.id,
                            "product_uom_qty": 18.0,
                            "product_uom": cls.product_9.uom_id.id,
                            "price_unit": 245.85,
                            "tax_id": False,
                            "sps_sequence": 2,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": cls.product_10.name,
                            "product_id": cls.product_10.id,
                            "product_uom_qty": 18.0,
                            "product_uom": cls.product_10.uom_id.id,
                            "price_unit": 245.85,
                            "tax_id": False,
                            "sps_sequence": 3,
                        },
                    ),
                ],
            }
        )
        cls.so_3.action_confirm()

        cls.so_2 = cls.so_model.create(
            {
                "partner_id": cls.ydesign.id,
                "currency_id": cls.env["res.currency"]
                .search([("name", "=", "EUR")])
                .id,
                "amount_untaxed": 750.0,
                "amount_total": 750.0,
                "sps_order_create_date": cls.today,
                "sps_client_order_ref": "L545454",
                "client_order_ref": "POSO2TEST",
                "incoterm": cls.env["account.incoterms"]
                .search([("code", "=", "EXW")], limit=1)
                .id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product_2.name,
                            "product_id": cls.product_2.id,
                            "product_uom_qty": 100.0,
                            "product_uom": cls.product_2.uom_id.id,
                            "price_unit": 5,
                            "tax_id": False,
                            "sps_sequence": 1,
                        },
                    )
                ],
            }
        )
        cls.so_2.action_confirm()

        cls.prod_cat1 = cls.prcat.create(
            {
                "name": "Basic Catalogue",
                "partner_id": cls.ydesign.id,
                "company_id": cls.gubi_as.id,
                "item_ids": [
                    (
                        0,
                        0,
                        {
                            "name": cls.product_1.name,
                            "lst_price": 100.0,
                            "categ_id": cls.product_1.categ_id.id,
                            "x_Collection": cls.prod_attr_val_1.id,
                            "x_Designed_by": cls.prod_attr_val_2.id,
                            "designed_in": 2020,
                        },
                    )
                ],
            }
        )

    @classmethod
    def _get_xml_to_test(cls, file_name):
        file_path = get_module_resource("gubi_edi_ubl", "tests/sample_files", file_name)
        with open(file_path, "rb") as file:
            content = file.read()
            xml_root = etree.fromstring(content.decode())
            return xml_root

    @classmethod
    def _do_picking(cls, picking, tracking_ref=None, date=None):
        """Do picking with only one move on the given date."""
        if not date:
            date = fields.Datetime.today()
        picking.action_confirm()
        for line in picking.move_lines:
            line.quantity_done = line.product_uom_qty
        if tracking_ref:
            picking.carrier_tracking_ref = tracking_ref
        picking.action_done()
        for move in picking.move_lines:
            move.date = date

    @classmethod
    def _create_product(cls, item_number, lst_price=0):
        return cls.product_model.create(
            {
                "name": "test product %s" % item_number,
                "item_number": item_number,
                "barcode": item_number * 2,
                "categ_id": cls.env.ref("product.product_category_all").id,
                "lst_price": lst_price,
            }
        )

    @classmethod
    def _create_attribute(cls, name, create_variant, display_type):
        return cls.attr.create(
            {
                "name": name,
                "create_variant": create_variant,
                "display_type": display_type,
            }
        )

    @classmethod
    def _create_partnerinfo(cls, partner, product, code, price):
        return cls.env["product.customerinfo"].create(
            {
                "name": partner.id,
                "product_id": product.id,
                "product_code": code,
                "price": price,
            }
        )

    # Incoming:

    def test_01_parse_ydesign_order(self):
        component = self.backend._find_component(
            "edi.backend",
            ["input.process"],
            backend_type="gubi_ubl",
            exchange_type="order_in",
        )
        xml_root = self._get_xml_to_test("Gubi_YDesign_850_v6.xml")
        res = component._parse_xml_file(xml_root)
        self.assertEqual(res.partner_id, self.ydesign)
        # TODO Check also actual time
        # self.assertEqual(res.date_order, datetime.datetime(2021, 6, 24))
        self.assertEqual(res.client_order_ref, "2259504506")
        self.assertEqual(res.sps_order_create_date, datetime.date(2021, 8, 3))
        self.assertEqual(res.commitment_date, datetime.datetime(2021, 8, 17, 0, 0))
        self.assertEqual(res.sps_transport_method_code, False)
        self.assertEqual(res.validity_date, False)
        self.assertEqual(res.note, "UPS")
        self.assertEqual(res.order_placed_by, False)
        self.assertEqual(res.sps_client_order_ref, "SO5925282")
        self.assertEqual(res.currency_id.name, "USD")
        self.assertEqual(res.partner_id.sps_customer_vendor_code, "3372967")
        self.assertEqual(res.partner_id.sps_transaction_code, "CITALLGUBILININ")
        # No correct invoice address in Ydesign document
        self.assertEqual(res.partner_invoice_id, self.ydesign_invoice)
        self.assertEqual(res.partner_shipping_id, self.ydesign_shipping)
        self.assertEqual(res.payment_term_id.name, "Net 30 days")
        self.assertEqual(len(res.order_line), 1)
        self.assertEqual(res.amount_untaxed, 371.25)
        # TODO taxes!
        # TODO requested ship and cancel dates

        self.assertEqual(res.order_line.product_id, self.product_1)
        self.assertEqual(res.order_line.price_unit, 371.25)
        self.assertEqual(res.order_line.product_uom_qty, 1.00)
        self.assertEqual(res.order_line.product_customer_code, "GUB2048744")
        self.assertEqual(res.order_line.sps_sequence, 1)

    def test_02_parse_dwr_order(self):
        component = self.backend._find_component(
            "edi.backend",
            ["input.process"],
            backend_type="gubi_ubl",
            exchange_type="order_in",
        )
        xml_root = self._get_xml_to_test("Gubi_DWR_850_v6.xml")
        res = component._parse_xml_file(xml_root)
        self.assertEqual(res.partner_id, self.dwr)
        self.assertEqual(res.client_order_ref, "PO9347045")
        # TODO Check also actual time
        # self.assertEqual(res.date_order, datetime.datetime(2021, 6, 29))
        self.assertEqual(res.sps_order_create_date, datetime.date(2021, 8, 3))
        self.assertEqual(res.commitment_date, datetime.datetime(2021, 10, 19, 0, 0))
        self.assertEqual(res.sps_transport_method_code, "O")
        self.assertEqual(res.note, "Ocean")
        self.assertEqual(res.sps_client_order_ref, "S02857911")
        self.assertEqual(res.validity_date, False)
        self.assertEqual(res.order_placed_by, False)
        self.assertEqual(res.currency_id.name, "USD")
        self.assertEqual(res.partner_id.sps_customer_vendor_code, "10040443")
        self.assertEqual(res.partner_id.sps_transaction_code, "FRQALLGUBILININ")
        self.assertEqual(res.partner_invoice_id, self.dwr_invoice)
        self.assertEqual(res.partner_shipping_id, self.dwr_shipping)
        self.assertEqual(res.payment_term_id.name, "Net 60 days")
        self.assertEqual(res.incoterm.code, "EXW")
        lines = list(res.order_line)
        self.assertEqual(len(lines), 1)
        # TODO taxes!
        # TODO requested ship and cancel dates
        self.assertEqual(lines[0].product_id, self.product_3)
        self.assertEqual(lines[0].sps_sequence, 1)
        self.assertAlmostEqual(lines[0].price_unit, 294.15)
        self.assertEqual(lines[0].product_uom_qty, 24)
        self.assertEqual(lines[0].product_customer_code, "100281808")

    # Outgoing:

    def test_11_ubl_advance_shipping_notification_generation(self):
        self.assertEqual(self.so_3.state, "sale")
        # Process delivery
        picking = self.so_3.picking_ids
        self.assertEqual(len(picking), 1)
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.dwr_backend.id),
                ("type_id", "=", self.type_sps_picking_out.id),
            ]
        )
        self.assertFalse(exchange)
        self._do_picking(picking, tracking_ref="ROH/OUT/1234")
        self.assertEqual(picking.state, "done")
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.dwr_backend.id),
                ("type_id", "=", self.type_sps_picking_out.id),
            ]
        )
        self.assertEqual(len(exchange), 1)

        file_content = exchange._get_file_content()
        xml_root = etree.fromstring(str.encode(file_content))
        ns = xml_root.nsmap

        picking_ref = xml_root.find("cbc:ID", namespaces=ns)
        self.assertEqual(picking_ref.text, picking.name)

        dropship_code = xml_root.find("cbc:DespatchAdviceTypeCode", namespaces=ns)
        self.assertEqual(dropship_code.text, "00")

        carrier_routing = xml_root.find("cbc:Note", namespaces=ns)
        self.assertEqual(carrier_routing.text, self.so_3.note)

        shipment_id = xml_root.find("cac:Shipment/cbc:ID", namespaces=ns)
        self.assertEqual(shipment_id.text, picking.carrier_tracking_ref)

        ship_date = xml_root.find(
            "cac:Shipment/cac:Delivery/cbc:ActualDeliveryDate", namespaces=ns
        )
        ship_date_str = datetime.datetime.strftime(
            picking.scheduled_date, "%Y-%m-%d %H:%M:%S"
        )
        self.assertEqual(ship_date.text, ship_date_str[:10])

        bill_of_lading = xml_root.find(
            "cac:AdditionalDocumentReference/cbc:ID", namespaces=ns
        )
        bill_of_lading_from_picking = picking.origin + "-" + ship_date_str[:10]
        self.assertEqual(bill_of_lading.text, bill_of_lading_from_picking)

        total_quantity = xml_root.find(
            "cac:Shipment/cbc:ConsignmentQuantity", namespaces=ns
        )
        picking_quantity = 0
        for line in picking.move_lines:
            picking_quantity += line.quantity_done
        self.assertEqual(total_quantity.text, str(picking_quantity))

        gross_weight = xml_root.find(
            "cac:Shipment/cbc:GrossWeightMeasure", namespaces=ns
        )
        self.assertEqual(gross_weight.text, str(picking.gross_weight))
        self.assertEqual(gross_weight.attrib["unitCode"], "KG")

        ship_street = xml_root.find(
            "cac:Shipment/cac:Delivery/cac:DeliveryAddress/cbc:StreetName",
            namespaces=ns,
        )
        self.assertEqual(ship_street.text, self.dwr_shipping.street)
        ship_city = xml_root.find(
            "cac:Shipment/cac:Delivery/cac:DeliveryAddress/cbc:CityName", namespaces=ns
        )
        self.assertEqual(ship_city.text, self.dwr_shipping.city)
        ship_zip = xml_root.find(
            "cac:Shipment/cac:Delivery/cac:DeliveryAddress/cbc:PostalZone",
            namespaces=ns,
        )
        self.assertEqual(ship_zip.text, self.dwr_shipping.zip)
        ship_state = xml_root.find(
            "cac:Shipment/cac:Delivery/cac:DeliveryAddress/cbc:CountrySubentity",
            namespaces=ns,
        )
        self.assertEqual(ship_state.text, self.dwr_shipping.state_id.name)
        ship_country = xml_root.find(
            "cac:Shipment/cac:Delivery/cac:DeliveryAddress/cac:Country/cbc:Name",
            namespaces=ns,
        )
        self.assertEqual(ship_country.text, self.dwr_shipping.country_id.name)
        origin_street = xml_root.find(
            "cac:Shipment/cac:OriginAddress/cbc:StreetName", namespaces=ns
        )
        self.assertEqual(origin_street.text, picking.company_id.street)
        origin_city = xml_root.find(
            "cac:Shipment/cac:OriginAddress/cbc:CityName", namespaces=ns
        )
        self.assertEqual(origin_city.text, picking.company_id.city)
        origin_zip = xml_root.find(
            "cac:Shipment/cac:OriginAddress/cbc:PostalZone", namespaces=ns
        )
        self.assertEqual(origin_zip.text, picking.company_id.zip)
        origin_state = xml_root.find(
            "cac:Shipment/cac:OriginAddress/cbc:CountrySubentity", namespaces=ns
        )
        self.assertEqual(origin_state.text, picking.company_id.state_id.name)
        origin_country = xml_root.find(
            "cac:Shipment/cac:OriginAddress/cac:Country/cbc:Name", namespaces=ns
        )
        self.assertEqual(origin_country.text, picking.company_id.country_id.name)
        transportation_method_code = xml_root.find(
            "cac:Shipment/cac:ShipmentStage/cbc:TransportMeansTypeCode", namespaces=ns
        )
        self.assertEqual(
            transportation_method_code.text, self.so_3.sps_transport_method_code
        )
        order_reference = xml_root.find("cac:OrderReference/cbc:ID", namespaces=ns)
        self.assertEqual(order_reference.text, self.so_3.client_order_ref)
        order_date = xml_root.find("cac:OrderReference/cbc:IssueDate", namespaces=ns)
        sps_order_date_str = datetime.datetime.strftime(
            self.so_3.sps_order_create_date, "%Y-%m-%d"
        )
        self.assertEqual(order_date.text, sps_order_date_str)
        customer_vendor_code = xml_root.find(
            "cac:DespatchSupplierParty/cbc:CustomerAssignedAccountID", namespaces=ns
        )
        self.assertEqual(
            customer_vendor_code.text, self.so_3.partner_id.sps_customer_vendor_code
        )
        xml_lines = xml_root.findall("cac:DespatchLine", namespaces=ns)
        picking_lines = list(picking.move_lines)
        line0_id = xml_lines[0].find("cbc:ID", namespaces=ns)
        self.assertEqual(line0_id.text, "PACK " + picking_lines[0].product_id.barcode)
        line0_sps_sequence = xml_lines[0].find(
            "cac:OrderLineReference/cbc:LineID", namespaces=ns
        )
        sps_sequence = self.so_3.order_line[0].sps_sequence
        self.assertEqual(line0_sps_sequence.text, str(sps_sequence))
        line0_quantity = xml_lines[0].find("cbc:DeliveredQuantity", namespaces=ns)
        self.assertEqual(line0_quantity.text, str(picking_lines[0].quantity_done))
        line0_item_vendor_code = xml_lines[0].find(
            "cac:Item/cac:SellersItemIdentification/cbc:ID", namespaces=ns
        )
        self.assertEqual(
            line0_item_vendor_code.text, picking_lines[0].product_id.item_number
        )
        line0_item_name = xml_lines[0].find("cac:Item/cbc:Description", namespaces=ns)
        self.assertEqual(line0_item_name.text, picking_lines[0].product_id.name)

        line1_id = xml_lines[1].find("cbc:ID", namespaces=ns)
        self.assertEqual(line1_id.text, "PACK " + picking_lines[1].product_id.barcode)
        line1_sps_sequence = xml_lines[1].find(
            "cac:OrderLineReference/cbc:LineID", namespaces=ns
        )
        sps_sequence = self.so_3.order_line[1].sps_sequence
        self.assertEqual(line1_sps_sequence.text, str(sps_sequence))
        line1_quantity = xml_lines[1].find("cbc:DeliveredQuantity", namespaces=ns)
        self.assertEqual(line1_quantity.text, str(picking_lines[1].quantity_done))
        line1_item_vendor_code = xml_lines[1].find(
            "cac:Item/cac:SellersItemIdentification/cbc:ID", namespaces=ns
        )
        self.assertEqual(
            line1_item_vendor_code.text, picking_lines[1].product_id.item_number
        )
        line1_item_name = xml_lines[1].find("cac:Item/cbc:Description", namespaces=ns)
        self.assertEqual(line1_item_name.text, picking_lines[1].product_id.name)

        line2_id = xml_lines[2].find("cbc:ID", namespaces=ns)
        self.assertEqual(line2_id.text, "PACK " + picking_lines[2].product_id.barcode)
        line2_sps_sequence = xml_lines[2].find(
            "cac:OrderLineReference/cbc:LineID", namespaces=ns
        )
        sps_sequence = self.so_3.order_line[2].sps_sequence
        self.assertEqual(line2_sps_sequence.text, str(sps_sequence))
        line2_quantity = xml_lines[2].find("cbc:DeliveredQuantity", namespaces=ns)
        self.assertEqual(line2_quantity.text, str(picking_lines[2].quantity_done))
        line2_item_vendor_code = xml_lines[2].find(
            "cac:Item/cac:SellersItemIdentification/cbc:ID", namespaces=ns
        )
        self.assertEqual(
            line2_item_vendor_code.text, picking_lines[2].product_id.item_number
        )
        line2_item_name = xml_lines[2].find("cac:Item/cbc:Description", namespaces=ns)
        self.assertEqual(line2_item_name.text, picking_lines[2].product_id.name)

    def test_12_ubl_invoice_generation(self):
        self.assertEqual(self.so_1.state, "sale")
        # Process delivery
        picking = self.so_1.picking_ids
        self._do_picking(picking, tracking_ref="ROH/OUT/1235")
        self.assertEqual(picking.state, "done")
        invoice = self.so_1.with_context()._create_invoices()
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft")
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.invoice_backend.id),
                ("type_id", "=", self.type_ubl_invoice_out.id),
            ]
        )
        self.assertFalse(exchange)
        invoice.post()
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.invoice_backend.id),
                ("type_id", "=", self.type_ubl_invoice_out.id),
            ]
        )
        self.assertEqual(len(exchange), 1)
        file_content = exchange._get_file_content()
        xml_root = etree.fromstring(str.encode(file_content))
        ns = xml_root.nsmap

        invoice_ref = xml_root.find("cbc:ID", namespaces=ns)
        self.assertEqual(invoice_ref.text, invoice.name)

        inv_date = xml_root.find("cbc:IssueDate", namespaces=ns)
        issue_date = datetime.datetime.strptime(inv_date.text, "%Y-%m-%d")
        self.assertEqual(issue_date.date(), invoice.invoice_date)

        inv_type_code = xml_root.find("cbc:InvoiceTypeCode", namespaces=ns)
        self.assertEqual(inv_type_code.text, "DR")

        inv_due_date = xml_root.find(
            "cac:PaymentMeans/cbc:PaymentDueDate", namespaces=ns
        )
        due_date = datetime.datetime.strptime(inv_due_date.text, "%Y-%m-%d")
        self.assertEqual(due_date.date(), invoice.invoice_date_due)

        payment_mode = xml_root.find(
            "cac:PaymentMeans/cbc:PaymentMeansCode", namespaces=ns
        )
        self.assertEqual(
            payment_mode.text, invoice.payment_mode_id.payment_method_id.unece_code
        )

        currency = xml_root.find("cbc:DocumentCurrencyCode", namespaces=ns)
        self.assertEqual(currency.text, invoice.currency_id.name)

        seller_vat = xml_root.find(
            "cac:AccountingSupplierParty/cac:Party/" "cac:PartyTaxScheme/cbc:CompanyID",
            namespaces=ns,
        )
        self.assertEqual(seller_vat.text, self.gubi_as.partner_id.vat)

        buyer_vat = xml_root.find(
            "cac:AccountingCustomerParty/cac:Party/" "cac:PartyTaxScheme/cbc:CompanyID",
            namespaces=ns,
        )
        self.assertEqual(buyer_vat.text, self.customer_1.vat)

        total_net_amount = xml_root.find(
            "cac:LegalMonetaryTotal/" "cbc:TaxExclusiveAmount", namespaces=ns
        )
        self.assertEqual(float(total_net_amount.text), invoice.amount_untaxed)

        total_amount = xml_root.find(
            "cac:LegalMonetaryTotal/cbc:PayableAmount", namespaces=ns
        )
        self.assertEqual(float(total_amount.text), invoice.amount_total)

        inv_lines = xml_root.findall("cac:InvoiceLine", namespaces=ns)
        self.assertEqual(len(inv_lines), 1)

        line = inv_lines[0]

        item_number = line.find(
            "cac:Item/cac:SellersItemIdentification/cbc:ID", namespaces=ns
        )
        self.assertEqual(
            item_number.text, invoice.invoice_line_ids.product_id.item_number
        )

        quantity = line.find("cbc:InvoicedQuantity", namespaces=ns)
        self.assertEqual(float(quantity.text), invoice.invoice_line_ids.quantity)

        unit_price = line.find("cac:Price/cbc:PriceAmount", namespaces=ns)
        self.assertEqual(float(unit_price.text), invoice.invoice_line_ids.price_unit)

        total_line_amount = line.find("cbc:LineExtensionAmount", namespaces=ns)
        self.assertEqual(
            float(total_line_amount.text), invoice.invoice_line_ids.price_subtotal,
        )

    def test_02_ubl_invoice_generation(self):
        self.assertEqual(self.so_2.state, "sale")
        # Process delivery
        picking = self.so_2.picking_ids
        self._do_picking(picking)
        self.assertEqual(picking.state, "done")
        invoice = self.so_2.with_context()._create_invoices()
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.state, "draft")
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.invoice_backend.id),
                ("type_id", "=", self.type_ubl_invoice_out.id),
            ]
        )
        self.assertFalse(exchange)
        invoice.post()
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.invoice_backend.id),
                ("type_id", "=", self.type_ubl_invoice_out.id),
            ]
        )
        self.assertEqual(len(exchange), 1)
        file_content = exchange._get_file_content()
        xml_root = etree.fromstring(str.encode(file_content))
        ns = xml_root.nsmap
        invoice_ref = xml_root.find("cbc:ID", namespaces=ns)
        self.assertEqual(invoice_ref.text, invoice.name)

        inv_date = xml_root.find("cbc:IssueDate", namespaces=ns)
        issue_date = datetime.datetime.strptime(inv_date.text, "%Y-%m-%d")
        self.assertEqual(issue_date.date(), invoice.invoice_date)

        inv_type_code = xml_root.find("cbc:InvoiceTypeCode", namespaces=ns)
        self.assertEqual(inv_type_code.text, "DR")

        sps_date = xml_root.find("cac:OrderReference/cbc:IssueDate", namespaces=ns)
        sps_order_date = datetime.datetime.strptime(sps_date.text, "%Y-%m-%d")
        self.assertEqual(sps_order_date.date(), self.so_2.sps_order_create_date)

        customer_order_ref = xml_root.find(
            "cac:OrderReference/cbc:CustomerReference", namespaces=ns
        )
        self.assertEqual(customer_order_ref.text, self.so_2.sps_client_order_ref)

        inv_due_date = xml_root.find(
            "cac:PaymentMeans/cbc:PaymentDueDate", namespaces=ns
        )
        due_date = datetime.datetime.strptime(inv_due_date.text, "%Y-%m-%d")
        self.assertEqual(due_date.date(), invoice.invoice_date_due)

        payment_mode = xml_root.find(
            "cac:PaymentMeans/cbc:PaymentMeansCode", namespaces=ns
        )
        self.assertEqual(
            payment_mode.text, invoice.payment_mode_id.payment_method_id.unece_code
        )

        currency = xml_root.find("cbc:DocumentCurrencyCode", namespaces=ns)
        self.assertEqual(currency.text, invoice.currency_id.name)

        seller_vat = xml_root.find(
            "cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            namespaces=ns,
        )
        self.assertEqual(seller_vat.text, self.gubi_as.partner_id.vat)

        buyer_vat = xml_root.find(
            "cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            namespaces=ns,
        )
        self.assertEqual(buyer_vat.text, self.ydesign.vat)

        sps_customer_vendor_code = xml_root.find(
            "cac:AccountingSupplierParty/cbc:CustomerAssignedAccountID", namespaces=ns,
        )
        self.assertEqual(
            sps_customer_vendor_code.text, self.ydesign.sps_customer_vendor_code
        )
        sps_transaction_code = xml_root.find(
            "cac:AccountingSupplierParty/cbc:AdditionalAccountID", namespaces=ns,
        )
        self.assertEqual(sps_transaction_code.text, self.ydesign.sps_transaction_code)

        total_net_amount = xml_root.find(
            "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount", namespaces=ns
        )
        self.assertEqual(float(total_net_amount.text), invoice.amount_untaxed)

        total_amount = xml_root.find(
            "cac:LegalMonetaryTotal/cbc:PayableAmount", namespaces=ns
        )
        self.assertEqual(float(total_amount.text), invoice.amount_total)

        inv_lines = xml_root.findall("cac:InvoiceLine", namespaces=ns)
        self.assertEqual(len(inv_lines), 1)

        line = inv_lines[0]

        sps_sequence = line.find("cbc:UUID", namespaces=ns)
        self.assertEqual(float(sps_sequence.text), self.so_2.order_line.sps_sequence)

        item_number = line.find(
            "cac:Item/cac:SellersItemIdentification/cbc:ID", namespaces=ns
        )
        self.assertEqual(
            item_number.text, invoice.invoice_line_ids.product_id.item_number
        )

        buyer_sku = line.find(
            "cac:Item/cac:BuyersItemIdentification/cbc:ID", namespaces=ns
        )
        self.assertEqual(buyer_sku.text, self.customerinfo_1[0].product_code)

        quantity = line.find("cbc:InvoicedQuantity", namespaces=ns)
        self.assertEqual(float(quantity.text), invoice.invoice_line_ids.quantity)

        unit_price = line.find("cac:Price/cbc:PriceAmount", namespaces=ns)
        self.assertEqual(float(unit_price.text), invoice.invoice_line_ids.price_unit)

        total_line_amount = line.find("cbc:LineExtensionAmount", namespaces=ns)
        self.assertEqual(
            float(total_line_amount.text), invoice.invoice_line_ids.price_subtotal,
        )

        # TODO: remit_to_address

    def test_01_ubl_catalogue_generation(self):
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.catalogue_backend.id),
                ("type_id", "=", self.type_ubl_catalogue_out.id),
            ]
        )
        self.assertFalse(exchange)
        catalogue = self.prod_cat1
        catalogue.send_product_button()
        exchange = self.exchange_model.search(
            [
                ("backend_id", "=", self.catalogue_backend.id),
                ("type_id", "=", self.type_ubl_catalogue_out.id),
            ]
        )
        self.assertEqual(len(exchange), 1)

        file_content = exchange._get_file_content()
        xml_root = etree.fromstring(str.encode(file_content))
        ns = xml_root.nsmap

        catalogue_name = xml_root.find("cbc:ID", namespaces=ns)
        self.assertEqual(catalogue_name.text, catalogue.name)

        catalogue_date = xml_root.find("cbc:IssueDate", namespaces=ns)
        issue_date = datetime.datetime.strptime(catalogue_date.text, "%Y-%m-%d")
        self.assertEqual(issue_date.date(), self.today.date())

        provider_vat = xml_root.find(
            "cac:ProviderParty/cac:PartyTaxScheme/cbc:CompanyID", namespaces=ns,
        )
        self.assertEqual(provider_vat.text, self.gubi_as.partner_id.vat)

        receiver_vat = xml_root.find(
            "cac:ReceiverParty/cac:PartyTaxScheme/cbc:CompanyID", namespaces=ns,
        )
        self.assertEqual(receiver_vat.text, self.ydesign.vat)

        catalogue_line = xml_root.findall("cac:CatalogueLine", namespaces=ns)
        self.assertEqual(len(catalogue_line), 1)

        line = catalogue_line[0]

        item_price = line.find("cac:ItemComparison/cbc:PriceAmount", namespaces=ns)
        self.assertEqual(float(item_price.text), self.product_1.lst_price)

        item_name = line.find("cac:Item/cbc:Name", namespaces=ns)
        self.assertEqual(item_name.text, self.product_1.name)

        item_number = line.find(
            "cac:Item/cac:SellersItemIdentification/cbc:ID", namespaces=ns
        )
        self.assertEqual(item_number.text, catalogue.item_ids.item_number)

        item_properties = line.findall("cac:KeywordItemProperty", namespaces=ns)
        for property in item_properties:
            if property[0].text == "Collection":
                self.assertEqual(property[1].text, catalogue.item_ids.x_Collection.name)
            elif property[0].text == "Designed By":
                self.assertEqual(
                    property[1].text, catalogue.item_ids.x_Designed_by.name
                )
            elif property[0].text == "Designed In":
                self.assertEqual(property[1].text, catalogue.item_ids.designed_in)

        # TODO: check if there is a custom pricelist for customer
        # TODO: Product attributes (attribute_line_ids one2many)
