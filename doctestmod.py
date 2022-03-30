#!/usr/bin/env python3

import os
import sys
import doctest
import argparse
import importlib


def import_module(filename):
    if os.path.exists(filename) or '/' in filename:
        sys.path.append(os.getcwd())
        module_name = os.path.splitext(filename)[0].replace('/', '.')
    else:
        module_name = filename
    return importlib.import_module(module_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--django', action='store_true')
    parser.add_argument('module')
    args = parser.parse_args()
    if args.django:
        sys.path.append('.')
        try:
            with open('manage.py', 'r') as fp:
                line = next(l for l in fp if l.strip().startswith('os.environ')
                            and 'DJANGO_SETTINGS_MODULE' in l)
        except (FileNotFoundError, StopIteration):
            parser.error('--django: No suitable manage.py found')
        exec(line.strip())
        import django
        django.setup()

    e, n = doctest.testmod(import_module(args.module))
    if e:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
