# coding=utf-8
#
# created by kpe on 10.01.2021 at 12:55 PM
#

from __future__ import division, absolute_import, print_function

import os
import sys
import json
import logging
import subprocess
from collections import defaultdict

import params as pp
import pyotp

from telerembash.bot import TeleRemBot


log = logging.getLogger(__name__)

COMMANDS = ['init', 'start']


class BotCli(pp.WithParams):
    class Params(TeleRemBot.Params):
        command = pp.Param(None, dtype=str, doc=f"command - one of: {COMMANDS}", positional=True)
        config = pp.Param("telerem.config.yaml", dtype=str, doc="config yaml file location")

    @property
    def params(self) -> Params:
        return self._params

    def _construct(self):
        self.command_handlers = defaultdict(lambda: self._cmd_not_found)
        self.command_handlers['init'] = self._do_init
        self.command_handlers['start'] = self._do_start

    def _cmd_not_found(self):
        log.error(f"Unrecognized command:[{self.params.command}]")

    def main(self):
        # pretty print non null arguments
        log.debug("main({})".format(json.dumps(dict(filter(lambda t: t[1] is not None,
                                                           dict(self.params).items())),
                                               indent=2)))
        # execute cli command
        self.command_handlers[self.params.command]()

    def _do_init(self):
        def filter_empty_values(d: dict):
            return dict(filter(lambda t: t[1] is not None, d.items()))

        def load_config():
            config = TeleRemBot.Params()
            config_path = self.params.config
            config_path = self.params.resolve_path(config_path)
            if os.path.isfile(config_path):
                log.info(f"Updating existing config at:[{config_path}]")
                config = TeleRemBot.Params.from_yaml_file(config_path)
            else:
                log.info(f"Creating new config at:[{config_path}]")
            config = filter_empty_values(dict(config))
            config.update(filter_empty_values(dict(self.params)))
            config = TeleRemBot.Params.from_dict(config, return_instance=True, return_unused=False)
            return config

        config = load_config()
        if config.auth_secret is None:
            log.warning("generating new AUTH_SECRET")
            config.auth_secret = pyotp.random_base32()
            self._provision_totp_secret(config.auth_secret)

        if config.api_token is None:
            log.warning("API_TOKEN was not specified")

        config.to_yaml_file(self.params.config)

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


def main():
    parser = BotCli.Params.to_argument_parser()
    args, _ = parser.parse_known_args()
    params = BotCli.Params(args._get_kwargs())
    cli = BotCli.from_params(params)
    cli.main()


if __name__ == '__main__':
    main()
