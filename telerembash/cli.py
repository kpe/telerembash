# coding=utf-8
#
# created by kpe on 10.01.2021 at 12:55 PM
#

from __future__ import division, absolute_import, print_function

import os
import re
import sys
import json
import string
import logging
import subprocess
from collections import defaultdict

import params as pp
import pyotp

from telerembash.bot import TeleRemBot
from telerembash.daemon import BotDaemon


log = logging.getLogger(__name__)

COMMANDS = ['init', 'start', 'install']


class BotCli(pp.WithParams):
    class Params(TeleRemBot.Params):
        command = pp.Param(None, dtype=str, doc=f"command - one of: {COMMANDS}", positional=True)
        config  = pp.Param("telerem.config.yaml", dtype=str, doc="config yaml file location")
        systemd = pp.Param(False, dtype=bool, doc=f"installs a systemd service")
        initd   = pp.Param(False, dtype=bool, doc=f"installs an init.d daemon script")

    @property
    def params(self) -> Params:
        return self._params

    def _construct(self):
        self.command_handlers = defaultdict(lambda: self._cmd_not_found)
        self.command_handlers['init'] = self._do_init
        self.command_handlers['start'] = self._do_start
        self.command_handlers['install'] = self._do_install

    def _cmd_not_found(self):
        log.error(f"Unrecognized command:[{self.params.command}]")

    def main(self):
        # pretty print non null arguments
        log.debug("main({})".format(json.dumps(dict(filter(lambda t: t[1] is not None,
                                                           dict(self.params).items())),
                                               indent=2)))
        # execute cli command
        self.command_handlers[self.params.command]()

    def _load_config(self):
        def filter_empty_values(d: dict):
            return dict(filter(lambda t: t[1] is not None, d.items()))

        config = TeleRemBot.Params()
        config_path = self.params.config
        config_path = self.params.resolve_path(config_path)
        if os.path.isfile(config_path):
            log.info(f"Loading existing config at:[{config_path}]")
            config = TeleRemBot.Params.from_yaml_file(config_path)
        else:
            log.info(f"Creating new config at:[{config_path}]")
        config = filter_empty_values(dict(config))
        config.update(filter_empty_values(dict(self.params)))
        config = TeleRemBot.Params.from_dict(config, return_instance=True, return_unused=False)
        return config

    def _do_init(self):
        config = self._load_config()
        if config.auth_secret is None:
            log.warning("generating new AUTH_SECRET")
            config.auth_secret = pyotp.random_base32()
            self._provision_totp_secret(config.auth_secret)

        if config.api_token is None:
            log.warning("API_TOKEN was not specified")

        config_path = self.params.resolve_path(self.params.config)
        config.to_yaml_file(config_path)
        log.debug(f"writing config to: {config_path}")

    def _provision_totp_secret(self, auth_secret: str):
        def local_user_and_host():
            username = 'user'
            hostname = 'host'
            try:
                username = os.environ['USER'] if 'USER' in os.environ else username
                hostname = os.environ['HOSTNAME'] if 'HOSTNAME' in os.environ else hostname
                username = subprocess.check_output(['whoami']).decode('utf8')
                hostname = subprocess.check_output(['hostname']).decode('utf8')
            except Exception as ex:
                log.warning("Failed to obtain user and hostname: {ex}")
            return username, hostname

        totp = pyotp.TOTP(auth_secret)

        # provision URI and QR code
        username, hostname = local_user_and_host()
        uri = totp.provisioning_uri(name=f"{username}@{hostname}", issuer_name=self.params.bot_name)
        sys.stdout.write(f"\n{uri}\n")
        self._dump_qr_code(uri)
        sys.stdout.write(f"TOTP setup key: {totp.secret}\n")
        sys.stdout.write("\n")
        sys.stdout.flush()

    @staticmethod
    def _dump_qr_code(uri: str):
        try:
            import qrcode
            qr = qrcode.QRCode()
            qr.add_data(uri)
            qr.print_tty()
        except ModuleNotFoundError as ex:
            log.warning("qrcode not found, try: `pip install qrcode`")

    def _do_start(self):
        params = TeleRemBot.Params.from_yaml_file(self.params.config)
        bot = TeleRemBot.from_params(params)
        bot.main()

    def _read_artifact(self, name):
        try:
            import importlib.resources as pkg_resources
        except ImportError:
            # for PY<37 try backported `importlib_resources`.
            import importlib_resources as pkg_resources
        from . import artifacts
        content = pkg_resources.read_text(artifacts, name)
        return content

    def _template_substitute(self, name: str, mapping: dict):
        return string.Template(self._read_artifact(name)).safe_substitute(mapping)

    def _escape_bash(self, content: str):
        return re.sub(r'\$(?!\{)', r'\$', content)

    def _do_install(self):
        config_path = self.params.resolve_path(self.params.config)
        if not os.path.exists(config_path):
            log.error(f"config not found, call init first: {config_path}")
            exit(2)
            return
        # dump the install script to stdout
        if not (self.params.systemd ^ self.params.initd):
            log.error("install needs a single --systemd or --initd CLI option")
            exit(2)
            return

        config = BotDaemon.Params.from_dict(self._load_config(), return_unused=False, return_instance=True)
        config.scripts_root = "${TELEREM_SCRIPTS_ROOT}"
        print(self._template_substitute("service-prepare.bash.template", {
            "_TELEREM_USER": config.service_user,
            "_TELEREM_HOME": f"/home/{config.service_user}",
            "_SERVICE_NAME": config.service_name,
            "_WELCOME_SCRIPT_CONTENT": self._escape_bash(self._read_artifact("welcome.sh.template")),
            "_TELEREMD_CONF_YAML_CONTENT": config.to_yaml_string()
        }))
        if self.params.initd:
            print(self._template_substitute("service-initd.bash.template", {
                "_INITD_SCRIPT_CONTENT": self._escape_bash(self._read_artifact("initd.template"))
            }))
        elif self.params.systemd:
            print(self._template_substitute("service-systemd.bash.template", {
                "_SYSTEMD_SERVICE_CONTENT": self._escape_bash(self._read_artifact("systemd.service.template"))
            }))


def main():
    def parse_cli_params(cls):
        args, _ = cls.to_argument_parser().parse_known_args()
        params = cls(args._get_kwargs())
        return params

    cli_cmd = parse_cli_params(BotCli.Params).command
    if cli_cmd in ["init", "start", "install"]:
        params = parse_cli_params(BotCli.Params)
        cli = BotCli.from_params(params)
        cli.main()
    elif cli_cmd in ["daemon"]:
        from telerembash.daemon import BotDaemonCli
        params = parse_cli_params(BotDaemonCli.Params)
        daemon = BotDaemonCli.from_params(params)
        daemon.main()
    else:
        BotCli.Params.to_argument_parser().print_usage()


if __name__ == '__main__':
    main()
