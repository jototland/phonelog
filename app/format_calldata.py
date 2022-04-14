from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math

from flask import g

from .parse_xml import HangupReasonT
from .db import get_db
from .utils import format_timedelta, min_not_taken, pretty_print_phone_no, uuid_expand


MAX_NO_ANSWER_BEFORE_WARN = 30 # seconds


def call_channels_for(call_session_id: str):
    if 'call_session_channels_cache' not in g:
        g.call_session_channels_cache = {}
    cache = g.call_session_channels_cache
    if call_session_id not in cache:
        call_channels = get_db().execute(
            sql_call_channels_joined,
            (call_session_id, )).fetchall()
        if call_channels:
            cache[call_session_id] = call_channels
    return cache[call_session_id]


def agent_name(call_channel) -> str:
    first_name = call_channel['agent_first_name']
    last_name = call_channel['agent_last_name']
    if first_name and last_name:
        return first_name + ' ' + last_name
    if first_name:
        return first_name
    if last_name:
        return last_name
    email = call_channel['agent_email']
    if email:
        return email
    return 'Unknown agent'


def agent_description(call_channel) -> str:
    name = agent_name(call_channel)
    loc = (call_channel['location_name']
           or call_channel['location_description']
           or 'Unknown internal phone')
    phno = call_channel['b_number']
    if name and loc:
        return f"«{name}», {loc} ({pretty_print_phone_no(phno)})"
    if name:
        return f"«{name}» ({pretty_print_phone_no(phno)})"
    if loc:
        return f"«Unknown agent», {loc} ({pretty_print_phone_no(phno)})"
    return f"{pretty_print_phone_no(phno)}"


def incoming_service_number(call_channel) -> str:
    descr = call_channel['service_number_description']
    if descr:
        return f"«{descr} ({pretty_print_phone_no(call_channel['b_number'])})»"
    return (f"Unknown service number "
            f"({pretty_print_phone_no(call_channel['b_number'])})")


def call_channel_incoming(call_channel):
    return call_channel['call_direction'] == 'i'


def call_channel_outgoing(call_channel):
    return (call_channel['end_point_class'] == 'e' and
            call_channel['call_direction'] == 'o')


def call_channel_to_agent(call_channel):
    return (call_channel['end_point_class'] == 'i'
            and call_channel['call_direction'] == 'o')


def a_phone_descr(call_channel):
    if call_channel_incoming(call_channel):
        if call_channel['service_number_id']:
            return incoming_service_number(call_channel)
    return pretty_print_phone_no(call_channel['b_number'])


class Category(Enum):
    NONE       = "none"
    CALL       = "call"
    WAIT       = "wait"
    ANSWER     = "answer"
    TALK       = "talking"
    HANGUP     = "hangup"
    UNFINISHED = "unfinished"

@dataclass
class Event:
    timestamp: float|None = None
    incoming: bool|None = None
    to_agent: bool|None = None
    to_service: bool|None = None
    answered: bool|None = None
    active: bool|None = None
    error: str = ""
    from_no: int|None = None
    to_no: int|None = None
    call_channel_no: int|None = None
    category: Category = Category.NONE
    from_descr: str|None = None
    to_descr: str|None = None
    column: int|None = None


@dataclass
class Row:
    timestamp: str
    cells: list


def get_call_session_data(call_session_id):
    call_channels = call_channels_for(call_session_id)
    if len(call_channels) == 0:
        return None

    start_time = call_channels[0]['call_timestamp']

    answered = False
    incoming = None
    from_no = None
    to_no = None

    agent_info = None
    service_info = None

    no_answer_time = 0
    error = call_channels[0]['hangup_reason'] not in (None, 'n')

    if call_channel_to_agent(call_channels[0]): # outgoing call
        incoming = False
        agent_info = agent_description(call_channels[0])
        if len(call_channels) >= 2:
            from_no = call_channels[1]['a_number']
            to_no = call_channels[1]['b_number']
            answered = call_channels[1]['answered']
    elif call_channel_incoming(call_channels[0]): # incoming call
        from_no = call_channels[0]['a_number']
        to_no = call_channels[0]['b_number']
        incoming = True
        service_info = call_channels[0]['service_number_description'] or 'Unknown service number'
        for i in range(1, len(call_channels)):
            if (call_channel_to_agent(call_channels[i]) and
                    call_channels[i]['answered']):
                agent_info = agent_description(call_channels[i])
                answered = True
                break
        else: # for:else
            if call_channels[0]['call_state'] == 't':
                no_answer_time = call_channels[0]['hangup_timestamp'] - start_time

    result = {
        'id': uuid_expand(call_session_id),
        'timestamp': start_time,
        'from_no': from_no,
        'from_descr': lookup_number(from_no),
        'to_no': to_no,
        'to_descr': lookup_number(to_no),
        'incoming': incoming,
        'active': call_channels[0]['active'],
        'agent_info': agent_info,
        'details': get_call_session_data_details(call_session_id),
    }
    if service_info:
        result['service_info'] = service_info
    if error:
        result['error'] = HangupReasonT(call_channels[0]['hangup_reason']).name
    if not answered and incoming and no_answer_time > MAX_NO_ANSWER_BEFORE_WARN:
        result['no_answer_time'] = math.ceil(no_answer_time)

    return result


def get_call_session_data_details(call_session_id):
    call_channels = call_channels_for(call_session_id)
    if len(call_channels) == 0:
        return None

    # for each call channel, generate up to three events (call, answer, end)
    events = []
    for call_channel_no, call_channel in enumerate(call_channels):
        active = call_channel['active']
        answered = call_channel['answered']
        error = ""
        if not call_channel['active'] and call_channel['hangup_reason'] not in (None, 'n'):
            error = HangupReasonT(call_channel['hangup_reason']).name

        kwargs = {}
        kwargs['incoming'] = call_channel['call_direction'] == 'i'
        kwargs['to_agent'] = call_channel['end_point_class'] == 'i'
        kwargs['to_service'] = call_channel['service_number_id'] is not None
        kwargs['answered'] = call_channel['answered']
        kwargs['active'] = call_channel['active']
        kwargs['error'] = error
        kwargs['from_no'] = call_channel['a_number']
        kwargs['to_no'] = call_channel['b_number']
        kwargs['call_channel_no'] = call_channel_no

        events.append(Event(
            timestamp = call_channel['call_timestamp'],
            category = Category.CALL,
            **kwargs
        ))
        if answered:
            events.append(Event(
                timestamp = call_channel['answer_timestamp'],
                category = Category.ANSWER,
                **kwargs
            ))
        if not active:
            events.append(Event(
                timestamp = call_channel['hangup_timestamp'],
                category = Category.HANGUP,
                **kwargs
            ))
        else:
            events.append(Event(
                timestamp = float('inf'),
                category = Category.UNFINISHED,
                **kwargs
            ))


    # lookup phone numbers for each event
    for event in events:
        event.from_descr = lookup_number(event.from_no)
        event.to_descr = lookup_number(event.to_no)

    # sort events in time, assign each call_channel to a column,
    # but try not to use too many columns
    events.sort(key = lambda x: x.timestamp)
    call_channels = list(map(lambda x: x.call_channel_no, events))
    columns_used = set()
    column_for = {}
    for event_no in range(len(events)):
        if call_channels[event_no] not in column_for:
            for prev_used_column in columns_used.copy():
                # FIXME: must also check if previous event in prev_used_column is completed,
                #        otherwise it will compact events that are not finished (yet)
                if prev_used_column not in call_channels[event_no:]:
                    columns_used.remove(prev_used_column)
            column_for[call_channels[event_no]] = min_not_taken(columns_used)
            columns_used.add(column_for[call_channels[event_no]])
        events[event_no].column = column_for[call_channels[event_no]]
    columns_count = max(column_for.values()) + 1

    # make a table of rows and columns
    rows = []
    for event in events:
        if (len(rows) >= 1
                and rows[-1].cells[event.column] is None
                and rows[-1].timestamp <= event.timestamp <= rows[-1].timestamp + 0.5
                ):
            rows[-1].cells[event.column] = event
        else:
            rows.append(Row(timestamp=event.timestamp, cells=[None]*columns_count))
            rows[-1].cells[event.column] = event

    # fill in the blanks
    for column_no in range(columns_count):
        for row_no in range(1, len(rows)):
            if (rows[row_no].cells[column_no] is None
                    and rows[row_no - 1].cells[column_no] is not None):
                if (rows[row_no - 1].cells[column_no].category
                    in (Category.CALL, Category.WAIT)):
                    new_category = Category.WAIT
                if (rows[row_no - 1].cells[column_no].category
                    in (Category.ANSWER, Category.TALK)):
                    new_category = Category.TALK
                else:
                    continue
                rows[row_no].cells[column_no] = Event(
                    category = new_category,
                    incoming = rows[row_no - 1].cells[column_no].incoming,
                    answered = rows[row_no - 1].cells[column_no].answered,
                    active = rows[row_no - 1].cells[column_no].active,
                    error = rows[row_no - 1].cells[column_no].error,
                )

    details = {}
    details['columns_count'] = columns_count
    details['rows'] = rows
    return details


def call_sessions_between(from_epoch, to_epoch):
    tuple_list = get_db().execute(
        'select call_session_id from call_sessions '
        'where start_timestamp >= ? '
        'and start_timestamp < ? '
        'order by start_timestamp desc',
        (from_epoch, to_epoch)).fetchall()
    return list(map(lambda x: x[0], tuple_list))


def newest_call_session_ids(seconds = 8 * 60 * 60):
    tuple_list = get_db().execute(
        'select call_session_id from call_sessions '
        'where start_timestamp >= ? '
        'order by start_timestamp desc',
        (datetime.utcnow().timestamp() - seconds, )).fetchall()
    return list(map(lambda x: x[0], tuple_list))


sql_call_channels_joined = """\
select
    call_channels.*,
    agents.agent_first_name agent_first_name,
    agents.agent_last_name agent_last_name,
    agents.agent_email agent_email,
    internal_phones.location_name location_name,
    internal_phones.location_description location_description,
    service_numbers.service_number_description service_number_description,
    from_service_numbers.service_number_description
        from_service_number_description
from call_channels
left outer join agents
    on agents.agent_id = call_channels.login_id
left outer join internal_phones
    on internal_phones.location_id = call_channels.location_id
left outer join service_numbers service_numbers
    on service_numbers.service_number_id = call_channels.service_number_id
left outer join service_numbers from_service_numbers
    on from_service_numbers.service_number = call_channels.a_number
where call_session_id = ?
order by call_timestamp
"""


def lookup_number(number) -> str:
    if 'number_lookup_cache' not in g:
        g.number_lookup_cache = {}
    cache = g.number_lookup_cache
    if number in cache:
        return cache[number]
    db = get_db()
    service_number = db.execute(
        "select service_number_description "
        "from service_numbers "
        "where service_number = ?",
        (number,)).fetchone()
    if service_number:
        (description,) = service_number
        cache[number] = description
        return cache[number]
    internal_phone = db.execute(
        "select location_name, location_description "
        "from internal_phones "
        "where location_number = ?",
        (number,)).fetchone()
    if internal_phone:
        name, description = internal_phone
        if name:
            cache[number] = name
        elif description:
            cache[number] = description
        else:
            cache[number] = 'Agent phone'
        return cache[number]
    contacts = db.execute(
        "select first_name, last_name "
        "from contacts "
        "where pstn_number = ? "
        "or gsm_number = ?",
        (number, number)).fetchone()
    if contacts:
        first_name, last_name = contacts
        if first_name and last_name:
            cache[number] = first_name + ' ' + last_name
            return cache[number]
        if first_name:
            cache[number] = first_name
            return cache[number]
        if last_name:
            cache[number] = last_name
            return cache[number]
    cache[number] = None
    return ''
