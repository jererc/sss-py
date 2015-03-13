#!/usr/bin/env python
import os
import argparse
import json
import subprocess
import re
from getpass import getuser

CACHE_FILENAME = 'cache.json'
SSH_CMD = ['ssh', '-A', '-o', 'PasswordAuthentication=no',
    '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=3']
BASENAME = os.path.splitext(os.path.basename(__file__))[0]
BIN_PATH = '/usr/local/bin'

try:
    from local_settings import *
except ImportError:
    pass


class bcolors(object):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Cache(object):

    def __init__(self):
        basepath = os.path.dirname(os.path.realpath(__file__))
        self.cache_file = os.path.join(basepath, CACHE_FILENAME)
        self._load_cache()

    def _load_cache(self):
        self.cache = {}
        if os.path.exists(self.cache_file):
            with open(self.cache_file) as fd:
                try:
                    self.cache = json.loads(fd.read())
                except ValueError:
                    pass

    def save(self, host, user):
        self.cache.setdefault(host, {'count': 0})
        self.cache[host]['user'] = user
        self.cache[host]['count'] += 1
        with open(self.cache_file, 'wb') as fd:
            fd.write(json.dumps(self.cache))

    def _search_regexes(self, regexes, value):
        for regex in regexes:
            if not regex.search(value):
                return False
        return True

    def iter_cache_hosts(self, hints):
        res = []
        re_hints = [re.compile(h, re.I) for h in hints]
        for host, info in self.cache.items():
            if self._search_regexes(re_hints, host):
                res.append((info['count'], host, info['user']))
        return sorted(res, reverse=True)

    def iter_hosts(self, hints):
        last = None

        if len(hints) == 1:
            if '@' in hints[0]:
                user, host = hints[0].split('@', 1)
            else:
                user = ''
                host = hints[0]

            cache_user = self.cache.get(host, {}).get('user')
            if cache_user:
                yield host, user or cache_user or getuser()
            else:
                last = host, user or getuser()

        for count, host, user in self.iter_cache_hosts(hints):
            yield host, user
        if last:
            yield last

def install():
    dst = os.path.join(BIN_PATH.rstrip('/'), BASENAME)
    if not os.path.exists(dst):
        try:
            os.symlink(os.path.realpath(__file__), dst)
            print 'created symlink %s' % dst
        except OSError, e:
            print 'failed to create symlink %s: %s' % (dst, str(e))

def connect(hints):
    cache = Cache()
    for host, user in cache.iter_hosts(hints):
        host_ = '%s@%s' % (user, host)
        res = subprocess.call(SSH_CMD + [host_, 'exit'])
        if res == 0:
            print '%sconnected to %s%s' % (bcolors.OKGREEN, host_, bcolors.ENDC)
            cache.save(host, user)
            subprocess.call(SSH_CMD + [host_])
            return
        print 'failed to connect to %s' % host_

def main():
    install()

    parser = argparse.ArgumentParser(description='SSH search')
    parser.add_argument('hints', nargs='+', type=str, help='host hints')
    args = parser.parse_args()
    connect(args.hints)


if __name__ == '__main__':
    main()
