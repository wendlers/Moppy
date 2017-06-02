import os
import sys
import pwd


def running_as_root():

    return os.geteuid() == 0


def run_as_root():

    if not running_as_root():

        args = ['sudo', sys.executable] + sys.argv + [os.environ]

        try:
            os.execlpe('sudo', *args)

        except Exception as e:

            print(e)
            sys.exit(1)


def drop_privileges(user_name, chfperm=None):

    if os.getuid() != 0:
        return 0, 0

    pwnam = pwd.getpwnam(user_name)

    if chfperm is not None:
        for f in chfperm:
            os.chown(f, pwnam.pw_uid, pwnam.pw_gid)

    os.setgroups([])

    os.setgid(pwnam.pw_gid)
    os.setuid(pwnam.pw_uid)

    os.umask(0o22)

    return pwnam.pw_uid, pwnam.pw_gid