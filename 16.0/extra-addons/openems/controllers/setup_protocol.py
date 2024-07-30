import base64

from odoo import http
from odoo.http import request


class SetupProtocol(http.Controller):
    @http.route("/openems_backend/sendSetupProtocolEmail", type="json", auth="user")
    def index(self, setupProtocolId, edgeId):
        setup_protocol_model = request.env["openems.setup_protocol"]
        setup_protocol_record = setup_protocol_model.search_read(
            [("id", "=", setupProtocolId)]
        )
        if len(setup_protocol_record) != 1:
            raise ValueError("Setup protocol not found for id [" + edgeId + "]")

        device_model = request.env["openems.device"]
        device_rec = device_model.search_read([("name", "=", edgeId)])
        if len(device_rec) != 1:
            raise ValueError("Device not found for id [" + edgeId + "]")

        name = (
            "IBN-"
            + edgeId
            + "-"
            + setup_protocol_record[0]["create_date"].strftime("%d.%m.%Y")
            + ".pdf"
        )

        data = request.env.ref(
            "openems.action_openems_setup_protocol_report"
        )._render_qweb_pdf([setupProtocolId])
        ibnPdf = request.env["ir.attachment"].create(
            {
                "res_model": "openems.device",
                "res_id": device_rec[0]["id"],
                "name": name,
                "store_fname": name,
                "datas": base64.b64encode(data[0]),
            }
        )

        templates = self.getTemplates(device_rec[0]['oem'], ibnPdf)

        templates['installer'].send_mail(setupProtocolId, force_send=True)
        templates['customer'].send_mail(setupProtocolId, force_send=True)

        return {}

    def getTemplates(self, oem: str, protocol):
        templates = {'customer': None, 'installer': None}

        templates['customer'] = request.env.ref(
            "openems.setup_protocol_email_customer")
        templates['installer'] = request.env.ref(
            "openems.setup_protocol_email_installer")

        logo = request.env.ref("openems.attachment_logo_openems")

        templates['customer'].attachment_ids = [
            (6, 0, [protocol.id, logo.id])]
        templates['installer'].attachment_ids = [
            (6, 0, [protocol.id, logo.id])]

        return templates

    @http.route('/openems_backend/get_latest_setup_protocol', type='json', auth='user')
    def get_latest_setup_protocol(self, edge_name):
        # search for device
        device_model = request.env['openems.device']
        device = device_model.search([('name', '=', edge_name)])

        response = dict()
        if not len(device.setup_protocol_ids) > 0:
            return response

        latest_protocol = device.setup_protocol_ids[0]

        # build customer object
        customer = latest_protocol.customer_id
        customer_values = dict({
            "firstname": customer['firstname'],
            "lastname": customer['lastname'],
            "email": customer['email'],
            "phone": customer['phone'],
            "address": {
                "street": customer['street'],
                "city": customer['city'],
                "zip": customer['zip'],
                "country": customer['country_id']['name']
            }
        })

        # check company for customer
        customer_company = customer['commercial_company_name']
        if customer_company:
            customer_values.update({
                "company": {
                    "name": customer['commercial_company_name']
                }
            })
        response.update({"customer": customer_values})

        # check different location is available
        location = latest_protocol['different_location_id']
        if location:
            location_values = dict({
                "firstname": location['firstname'],
                "lastname": location['lastname'],
                "email": location['email'],
                "phone": location['phone'],
                "address": {
                    "street": location['street'],
                    "city": location['city'],
                    "zip": location['zip'],
                    "country": location['country_id']['name']
                }
            })

            # check company for different location
            different_location_company = location['commercial_company_name']
            if different_location_company:
                location_values.update({
                    "company": {
                        "name": location['commercial_company_name']
                    }
                })
            response.update({"location": location_values})

        # build items object
        items = list()
        for item in latest_protocol.item_ids:
            items.append({
                "view": item['view'],
                "field": item['field'],
                "category": item['category'],
                "name": item['name'],
                "value": item['value']
            })
        response.update({"items": items})

        return response
