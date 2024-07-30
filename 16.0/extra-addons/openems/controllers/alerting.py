import logging
from datetime import  datetime
from enum import Enum

from odoo import http
from odoo.http import request

class SumState(Enum):
    FAULT = 0 
    WARNING = 1

class Message:
    sentAt: datetime
    edgeId: str
    userIds: list[int]

    def __init__(self, sentAt: datetime, edgeId: str, userIds: list[int]) -> None:
        self.sentAt = sentAt
        self.edgeId = edgeId
        self.userIds = userIds
        
class SumStateMessage(Message):
    state: SumState
    
    def __init__(self, sentAt: datetime, edgeId: str, userIds: list[int], state: SumState) -> None:
        super().__init__(sentAt, edgeId, userIds)
        self.state = state

class Alerting(http.Controller):
    __logger = logging.getLogger("Alerting")

    @http.route("/openems_backend/mail/alerting_sum_state", type="json", auth="user")
    def sum_state_alerting(self, sentAt: str, params: list[dict]):
        msgs = self.__get_sum_state_params(sentAt, params)
        update_func = lambda role, at: { role.write({"sum_state_last_notification": at})}
        
        if len(msgs) == 0:
            self.__logger.error("Scheduled SumState-Alerting-Mail without any recipients!!!")
        
        template = request.env.ref('openems.alerting_sum_state')
        for msg in msgs:
            self.__send_mails(template, msg, update_func)
                  
        return {}

    @http.route("/openems_backend/mail/alerting_offline", type="json", auth="user")
    def offline_alerting(self, sentAt: str, params: list[dict]):
        msgs = self.__get_offline_params(sentAt, params)
        update_func = lambda role, at: { role.write({"offline_last_notification": at})}

        template = request.env.ref("openems.alerting_offline")
        for msg in msgs:
            self.__send_mails(template, msg, update_func)

        return {}

    def __get_offline_params(self, sentAt, params) -> list[Message]:
        msgs = list()
        sent = datetime.strptime(sentAt, "%Y-%m-%d %H:%M:%S")
        for param in params:
            edgeId = param["edgeId"]
            recipients = param["recipients"]
            msgs.append(Message(sent, edgeId, recipients));
        return msgs
    
    def __get_sum_state_params(self, sentAt, params) -> list[SumStateMessage]:
        msgs = list()
        sent = datetime.strptime(sentAt, "%Y-%m-%d %H:%M:%S")
        for param in params:
            edgeId = param["edgeId"]
            recipients = param["recipients"]
            state = param["state"]
            msgs.append(SumStateMessage(sent, edgeId, recipients, state));
        return msgs

    def __send_mails(self, template, msg: Message, update_func):
        roles = http.request.env['openems.alerting'].search(
            [('user_id','in',msg.userIds),('device_id','=',msg.edgeId)]
        )
        
        for role in roles:
            try:
                template.send_mail(res_id=role.id, force_send=True)
                update_func(role, msg.sentAt)
            except Exception as err:
                self.__logger.error("[" + str(err) + "] Unable to send template[" + str(template.name) +"] to edgeUser[user=" + str(role.id) + ", edge=" + str(msg.edgeId)+ "]")