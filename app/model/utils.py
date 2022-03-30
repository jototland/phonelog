from typing import NamedTuple
from itertools import chain


def generate_namedtuple(name, fields):
    return NamedTuple(name,
                      map(lambda t: t[:2], fields))


def generate_create_table_sql(name, fields):
    columns = ", ".join(map(lambda t: t[0]+' '+t[2], fields))
    return f"""create table {name} ({columns}) without rowid;"""


def generate_upsert_sql(tablename, fields, primary=()):
    field_names = tuple(map(lambda x: x[0], fields))
    remaining_fields = tuple(filter(
        lambda x: x not in primary,
        field_names))
    return " ".join(chain(
        [f"insert into {tablename} ({', '.join(field_names)})",
         f"values({', '.join(['?' for _ in field_names])})",
         f"on conflict ({', '.join(primary)}) do update set",],
        [", ".join(f"{f} = excluded.{f}" for f in remaining_fields)]))
