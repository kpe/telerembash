# coding=utf-8
#
# created by kpe on 10.01.2021 at 12:55 PM
#

from __future__ import division, absolute_import, print_function

import os
import sys
import logging

import params as pp
import daemon
import lockfile

from telerembash.bot import TeleRemBot


log = logging.getLogger(__name__)


class BotDaemonCli(pp.WithParams):
    class Params(pp.Params):
        daemon = pp.Param(None, dtype=str, doc=f"first positional should be daemon", positional=True)
        command = pp.Param(None, dtype=str, doc=f"one of - start, stop", positional=True)
        config = pp.Param("/etc/teleremd.config.yaml", dtype=str, doc="teleremd daemon config")

    @property
    def params(self) -> Params:
        return self._params

    def main(self):
        if not os.path.isabs(self.params.config) or not os.path.exists(self.params.config):
            print(f"invalid config path: {self.params.config}")
            exit(3)
        params = BotDaemon.Params.from_yaml_file(self.params.config)
        daemon_cli = BotDaemon.from_params(params)
        cli_cmd = self.params.command
        if cli_cmd in ["start"]:
            daemon_cli.start()
        elif cli_cmd in ["stop"]:
            daemon_cli.stop()
        else:
            print(f"unknown daemon command: {cli_cmd}")
            exit(4)


class BotDaemon(pp.WithParams):
    class Params(TeleRemBot.Params):
        service_name = pp.Param("teleremd", dtype=str, doc=f"(install only) name of the service/daemon")
        service_user = pp.Param("teleremd", dtype=str, doc=f"(install only) user for the service/daemon")
        pid_file = pp.Param(None, dtype=str, doc=f"pidfile for the daemon")

        def get_home_dir(self):
            import pwd
            home_dir = pwd.getpwnam(self.service_user).pw_dir
            return home_dir

        def get_pid_file(self):
            pid_file = f"/run/{self.service_name}/{self.service_name}.pid" if self.pid_file is None else self.pid_file
            return pid_file

    def start(self):
        import pwd
        params = self.params
        with daemon.DaemonContext(
            # pidfile=lockfile.FileLock(params.get_pid_file()),
            working_directory=params.get_scripts_root(),
            uid=pwd.getpwnam(params.service_user).pw_uid,
            umask=0o0133,
            detach_process=True,

            stderr=sys.stderr,
            stdout=sys.stdout
        ):
            with open(params.get_pid_file(), "wt") as pid_file:
                print(str(os.getpid()), file=pid_file)

            bot = TeleRemBot.from_params(params)
            bot_params = dict(filter(lambda x: x[0] not in ['api_token', 'auth_secret'], bot.params.items()))
            log.info(f"starting daemon bot {bot_params}")
            bot.main()


def main():
    pass


if __name__ == "__main__":
    main()
