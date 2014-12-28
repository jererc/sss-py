#!/usr/bin/env python
import os
import argparse
import json
import subprocess
import re
import getpass


BIN_PATH = '/usr/local/bin'
USERS = []
DOMAINS = ['']
CACHE_FILENAME = 'cache.json'
SSH_CMD = ['ssh', '-A', '-o', 'ConnectTimeout=5']
BASENAME = os.path.splitext(os.path.basename(__file__))[0]
RE_RANGE = re.compile(r'(\[(\d+)-(\d+)\])')

try:
    from local_settings import *
except ImportError:
    pass


class Cache(object):

    def __init__(self):
        basepath = os.path.dirname(os.path.realpath(__file__))
        self.cache_file = os.path.join(basepath, CACHE_FILENAME)

    def _get_cache(self):
        cache = {}
        if os.path.exists(self.cache_file):
            with open(self.cache_file) as fd:
                try:
                    cache = json.loads(fd.read())
                except ValueError:
                    pass
        return cache

    def save(self, cache):
        hosts = self._get_cache()
        hosts.update(cache)
        with open(self.cache_file, 'wb') as fd:
            fd.write(json.dumps(hosts))

    def get_host_info(self, host):
        info = self._get_cache().get(host)
        if info is None:
            domains = DOMAINS
            users = USERS or [getpass.getuser()]
        else:
            domain = info['domain']
            domains = [domain] + [v for v in DOMAINS if v != domain]
            user = info['user']
            users = [user] + [v for v in USERS if v != user]
        return domains, users


class Term(object):

    SCRIPT_MAIN = """tell application "iTerm"
        tell the current terminal
    %s
        end tell
    end tell
    """
    SCRIPT_TAB = """
            launch session "Default Session"
            tell the last session
                %s
            end tell
    """
    SCRIPT_CMD = """
                write text \"%s\"
    """

    def __init__(self, hosts, extra_cmd, tabs_count=1):
        def get_cmds(host):
            cmd = '%s %s' % (BASENAME, host)
            return (cmd, extra_cmd) if extra_cmd else (cmd,)

        self.tab_cmds = []
        for host in hosts:
            for i in range(tabs_count):
                self.tab_cmds.append(get_cmds(host))

    def get_script(self):
        script_tabs = [self.SCRIPT_TAB % ''.join([self.SCRIPT_CMD % c for c in tc])
            for tc in self.tab_cmds]
        return self.SCRIPT_MAIN % ''.join(script_tabs)

    def start(self):
        cmd = ['osascript']
        script = self.get_script()
        for line in script.splitlines():
            if line.strip():
                cmd.extend(['-e', line])
        return subprocess.call(cmd)


def install():
    dst = os.path.join(BIN_PATH.rstrip('/'), BASENAME)
    if not os.path.exists(dst):
        try:
            os.symlink(os.path.realpath(__file__), dst)
            print 'created symlink %s' % dst
        except OSError, e:
            print 'failed to create symlink %s: %s' % (dst, str(e))

def get_hosts(hosts):
    hosts_ = []
    for host in hosts:
        res = RE_RANGE.search(host)
        if not res:
            hosts_.append(host)
        else:
            for i in range(int(res.group(2)), int(res.group(3)) + 1):
                hosts_.append(RE_RANGE.sub(str(i), host))
    return hosts_

def connect(hostname):
    cache = Cache()
    domains, users = cache.get_host_info(hostname)
    for domain in domains:
        for user in users:
            host = '%s@%s%s' % (user, hostname, '.%s' % domain if domain else '')
            res = subprocess.call(SSH_CMD + [host])
            if res == 0:
                cache.save({hostname: {
                        'user': user,
                        'domain': domain,
                        }})
                return
            print 'failed to connect to %s' % host
    print 'failed to connect to %s' % hostname

def main():
    parser = argparse.ArgumentParser(description='Open SSH sessions.')
    parser.add_argument('hosts', metavar='host', type=str, nargs='*',
            help='list of hostnames (accepts [x-y] range wildcard)')
    parser.add_argument('-c' ,'--extra_cmd', type=str,
            help='extra command')
    parser.add_argument('-t' ,'--tabs_count', type=int, default=1,
            help='number of tabs per host')
    args = parser.parse_args()

    install()

    if not args.hosts:
        print 'missing hosts'
        return

    hosts = get_hosts(args.hosts)
    print 'connecting to %s' % ', '.join(hosts)

    if len(hosts) == 1 and args.tabs_count == 1:
        connect(hosts[0])
    else:
        Term(hosts, extra_cmd=args.extra_cmd,
                tabs_count=args.tabs_count).start()


if __name__ == '__main__':
    main()
