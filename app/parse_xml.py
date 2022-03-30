from datetime import datetime
from enum import Enum

import lxml.etree

from .model.call_data import CallChannel, CallSession
from .model.contacts import Contact
from .model.customer_data import Agent, InternalPhone, ServiceNumber
from .utils import e164_to_int, iso_datetime_to_epoch, str_to_bool, uuid_compact, uuid_expand


def parse_contacts(xmldata: bytes):
    contacts = []
    data = lxml.etree.fromstring(xmldata)
    now = datetime.utcnow().timestamp()
    for contact in data.xpath('Contacts/Contact'):
        if (id := subint(contact, 'ContactId')):
            contacts.append(Contact(
                contact_id = id,
                first_name = subtext(contact, 'FirstName'),
                last_name = subtext(contact, 'LastName'),
                email = subtext(contact, 'Email'),
                pstn_number = subphone(contact, 'Number'),
                gsm_number = subphone(contact, 'GsmNumber'),
                company = subtext(contact, 'Company'),
                comments = subtext(contact, 'Comments'),
                title = subtext(contact, 'Title'),
                department = subtext(contact, 'Department'),
                address = subtext(contact, 'Address'),
                editable = subbool(contact, 'Editable'),
                contact_last_updated = now
            ))
    return contacts


def parse_customer_data(xmldata: bytes):
    agents, internal_phones, service_numbers = [], [], []
    data = lxml.etree.fromstring(xmldata)
    now = datetime.utcnow().timestamp()
    for login in data.xpath('Logins/Login'):
        if (id := subint(login, 'LoginId')):
            agents.append(Agent(agent_id = id,
                                agent_first_name = subtext(login, 'Firstname'),
                                agent_last_name = subtext(login, 'LastName'),
                                agent_email = subtext(login, 'Email'),
                                agent_last_updated = now,
                                ))
    for location in data.xpath('Locations/Location'):
        if (id := subint(location, 'LocationId')):
            internal_phones.append(InternalPhone(
                location_id = id,
                location_number = (subphone(location, 'FixedNumber')
                          or subphone(location, 'PstnNumber')
                          or subphone(location, 'GsmNumber')),
                location_name = subtext(location, 'LocationName'),
                location_description = subtext(location, 'Description'),
                location_last_updated = now,
            ))
    for service_number in data.xpath('ServiceNumbers/ServiceNumber'):
        if (id := subint(service_number, 'ServiceNumberId')):
            service_numbers.append(ServiceNumber(
                service_number_id = id,
                service_number = subphone(service_number, 'Number'),
                service_number_description = subtext(service_number, 'Description'),
                service_number_last_updated = now,
            ))
    return agents, internal_phones, service_numbers


def subtext(node: lxml.etree, sub: str) -> str|None:
    if len(subnodes := node.xpath(sub)) == 0:
        return None
    if subnodes[0].text is None:
        return None
    return subnodes[0].text.strip()


def subuuid(node: lxml.etree, sub: str) -> str:
    return uuid_compact(subtext(node, sub) or 'failure')


def subtimestamp(node: lxml.etree, sub: str) -> float|None:
    if (text := subtext(node, sub)) is None:
        return None
    return iso_datetime_to_epoch(text)


def subbool(node: lxml.etree, sub: str) -> int|None:
    if (text := subtext(node, sub)) is None:
        return None
    return str_to_bool(text)


def subint(node: lxml.etree, sub: str) -> int|None:
    if (text := subtext(node, sub)) is None:
        return None
    return int(text)

def subphone(node: lxml.etree, sub: str) -> int|None:
    if (text := subtext(node, sub)) is None:
        return None
    return e164_to_int(text)


class CallDirectionT(Enum):
    incoming = 'i'
    outgoing = 'o'


class EndPointClassT(Enum):
    internal = 'i'
    external = 'e'


class CallStateT(Enum):
    proceeding = 'p'
    ringing = 'r'
    established = 'e'
    terminated = 't'


class HangupByT(Enum):
    caller = 'c'
    callee = 'r'


class HangupReasonT(Enum):
    normal = 'n'
    canceled = 'c'
    busy = 'b'
    redirected = 'r'
    invalidnumber = 'i'
    declined = 'd'
    timeout = 't'
    failed = 'f'


def subenum(node: lxml.etree, enumtype) -> str|None:
    sub = enumtype.__name__[:-1]
    if (text := subtext(node, sub)) is None:
        return None
    return enumtype[text.lower()].value


service_number_id_xpath_query = """\
ServiceNumbers /
ServiceNumber /
CallChannelId [ normalize-space(text()) = $call_channel_id ] /
parent :: node() /
Number [ normalize-space(text()) = $phone_number ] /
parent :: node() /
ServiceNumberId"""


def get_service_number_id(call_session: lxml.etree._Element,
                      call_channel_id: str,
                      phone_number: int|None) -> int|None:
    if not phone_number:
        return
    service_number_id_nodes = call_session.xpath(
        service_number_id_xpath_query,
        call_channel_id = uuid_expand(call_channel_id),
        phone_number = "+" + str(phone_number),
    )
    if len(service_number_id_nodes) >= 1:
        return int(service_number_id_nodes[0].text)
    return None


def parse_call_data(xmldata: bytes):
    call_sessions, call_channels = [], []
    data = lxml.etree.fromstring(xmldata)
    for call_session in data.xpath('CallSession'):
        call_session_id = subuuid(call_session, 'CallSessionId')
        call_sessions.append(CallSession(
            call_session_id = call_session_id,
            start_timestamp = subtimestamp(call_session, 'StartTimestamp'),
            end_timestamp = subtimestamp(call_session, 'EndTimestamp'),
        ))
        for call_channel in call_session.xpath('CallChannels/CallChannel'):
            call_channel_id = subuuid(call_channel, 'CallChannelId')
            a_number = subphone(call_channel, 'ANumber')
            b_number = subphone(call_channel, 'BNumber')
            call_channels.append(CallChannel(
                call_channel_id = call_channel_id,
                call_session_id = call_session_id,
                call_direction = subenum(call_channel, CallDirectionT),
                a_number = a_number,
                b_number = b_number,
                end_point_class = subenum(call_channel, EndPointClassT),
                call_state = subenum(call_channel, CallStateT),
                active = subbool(call_channel, 'Active'),
                answered = subbool(call_channel, 'Answered'),
                hangup_by = subenum(call_channel, HangupByT),
                hangup_reason = subenum(call_channel, HangupReasonT),
                call_timestamp = subtimestamp(call_channel, 'CallTimestamp'),
                ringing_timestamp = subtimestamp(call_channel, 'RingingTimestamp'),
                answer_timestamp = subtimestamp(call_channel, 'AnswerTimestamp'),
                hangup_timestamp = subtimestamp(call_channel, 'HangupTimestamp'),
                login_id = subint(call_channel, 'LoginId'),
                location_id = subint(call_channel, 'LocationId'),
                device_id = subint(call_channel, 'DeviceId'),
                service_number_id = get_service_number_id(
                    call_session, call_channel_id, b_number),
            ))
    return call_sessions, call_channels
