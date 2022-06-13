from base64 import b85decode, b85encode
from datetime import datetime, timezone
import json
import math
import re
from uuid import UUID

from dateutil.parser import parse as parse_iso_date


def get_conversion(converter, value, fallback=None):
    try:
        return converter(value)
    except:
        return fallback


def uuid_compact(uuid_string: str) -> str:
    return b85encode(UUID(uuid_string).bytes).decode(encoding='ascii')


def uuid_expand(compact_uuid: str) -> str:
    return str(UUID(bytes=b85decode(compact_uuid)))


def iso_datetime_to_epoch(iso_datetime: str) -> float:
    return parse_iso_date(iso_datetime).timestamp()


def str_to_bool(text: str) -> bool:
    if text.lower().strip() == 'true':
        return True
    if text.lower().strip() == 'false':
        return False
    raise ValueError(f"'{text}' is not 'True' or 'False'")


_e164_regexp = re.compile(r'^\+\d{2,15}$')
def e164_to_int(e164_phone_number: str) -> int:
    if _e164_regexp.match(e164_phone_number):
        return int(e164_phone_number[1:])
    raise ValueError("'{e164_string}' is not a phone number in full E.164 format")


def int_to_e164(phone_number_int: int) -> str:
    return f"+{phone_number_int}"


def prettify_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_timedelta(seconds):
    """formats `seconds` with minutes and seconds

    >>> format_timedelta(12)
    '12 seconds'
    >>> format_timedelta(63)
    '1 minute and 3 seconds'
    >>> format_timedelta(120)
    '2 minutes and 0 seconds'
    >>> format_timedelta(181)
    '3 minutes and 1 second'
    """
    minutes = math.floor(seconds / 60)
    seconds = round(seconds % 60)

    minutes_text = ''
    if minutes > 1:
        minutes_text = f"{minutes} minutes"
    elif minutes == 1:
        minutes_text = '1 minute'

    seconds_text = ''
    if seconds > 1 or seconds == 0:
        seconds_text = f"{seconds} seconds"
    elif seconds == 1:
        seconds_text = '1 second'

    if minutes:
        return f"{minutes_text} and {seconds_text}"
    return seconds_text


def format_date(epoch):
    return (
        datetime.fromtimestamp(epoch, tz=timezone.utc)
        .astimezone(pytz.timezone('Europe/Oslo'))
        .strftime('%Y-%m-%d')
    )


def format_time(epoch):
    return (
        datetime.fromtimestamp(epoch, tz=timezone.utc)
        .astimezone(pytz.timezone('Europe/Oslo'))
        .strftime('%H:%M:%S')
    )


def separate_groups(value, *groups, sep='\u00a0'):
    """splits `value` into shorter strings, separated by `sep`.
    Each group has the length given by `*groups`.
    If `groups` don't sum up to lengt of `value`, return `value`

    >>> separate_groups('conundrum', 3, 2, 2, 2, sep=' ')
    'con un dr um'
    >>> separate_groups('conundrum', 1, 2, 2, 2, sep=' ')
    'conundrum'
    """
    value = str(value)
    if len(value) != sum(groups):
        return value
    starts = [sum(groups[0:g]) for g in range(len(groups))]
    ends = [g+s for (g,s) in zip(groups, starts)]
    return sep.join(value[s:e] for (s,e) in zip(starts, ends))


PHONE_GROUPINGS = {
    re.compile(r'^447\d{9}$'): [2,4,3,3],
    re.compile(r'^45\d{8}$') : [2,2,2,2,2],
    re.compile(r'^468\d{6}$') : [2,1,2,2,2],
    re.compile(r'^468\d{7}$') : [2,1,3,2,2],
    re.compile(r'^468\d{8}$') : [2,1,3,3,1],
    re.compile(r'^46[012345679]\d{8}$') : [2,2,3,2,2],
    re.compile(r'^46[123456790]\d{6}$') : [2,2,3,2],
    re.compile(r'^475[89]\d{10}$') : [2,4,4,4],
    re.compile(r'^47[123567]\d{7}$') : [2,2,2,2,2],
    re.compile(r'^47[489]\d{7}$') : [2,3,2,3],
}


def pretty_print_phone_no(number, sep='\u00a0'):
    """format phone `number` according to E.123 and local custom,
    with separator `sep` (defaults to no break space)

    >>> pretty_print_phone_no(4790000000, sep=' ')
    '+47 900 00 000'
    >>> pretty_print_phone_no(46700000000, sep='_')
    '+46_70_000_00_00'
    >>> pretty_print_phone_no(4790000)
    '+4790000'
    """
    number = str(number)
    for k in PHONE_GROUPINGS.keys():
        if k.match(number):
            return "+" + separate_groups(number,
                                         *PHONE_GROUPINGS[k],
                                         sep=sep)
    return "+" + number



# NO https://www.gulesider.no/api/u2?number=%2B{number}&profile=no
# DK https://www.krak.dk/api/ps?query=%2B{number}&sortOrder=default&profile=krak&page=1&lat=0&lng=0&limit=25&client=true
# SE https://www.eniro.se/api/cs?device=desktop&query=%2B{number}&sortOrder=default&profile=se&page=1&lat=0&lng=0&limit=25&review=0&webshop=false&client=true

def phone_number_lookup_link(number):
    sn = str(number)
    if sn.startswith('47'):
        return f'<a href="https://www.1881.no/?query={sn[2:]}" target="_blank" data-tooltip data-bs-placement="top" data-title-i18n="Search for number in 1881.no">{pretty_print_phone_no(number)}</a>'
    elif sn.startswith('46'):
        return f'<a href="https://www.hitta.se/s%C3%B6k?vad=0{sn[2:]}" target="_blank" data-tooltip data-bs-placement="top" data-title-i18n="Search for number in hitta.se">{pretty_print_phone_no(number)}</a>'
    elif sn.startswith('45'):
        return f'<a href="https://118.dk/search/go?what={sn[2:]}" target="_blank" data-tooltip data-bs-placement="top" data-title-i18n="Search for number 118.dk">{pretty_print_phone_no(number)}</a>'
    return pretty_print_phone_no(number)


def min_not_taken(numbers):
    """returns the smallest natural number not already in `numbers`

    >>> min_not_taken([1,2,3])
    0
    >>> min_not_taken([5,4,2,1,0])
    3
    >>> min_not_taken([0,2,1])
    3
    """
    max_used = 0
    try:
        max_used = max(numbers)
    except ValueError:
        return 0
    for i in range(max_used):
        if i not in numbers:
            return i
    return max_used + 1
