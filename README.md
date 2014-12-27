Open SSH sessions in iTerm2 tabs.


Set users and domains in local_settings.py file:

        USERS = ['jererc', 'root']
        DOMAINS = ['dev.domain.com', 'admin.domain.com']


Examples:

        sss host1 host2 host3
        sss host[1-3]
        sss host1 -t 3 -c "cd mydir"
