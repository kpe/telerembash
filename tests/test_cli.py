# coding=utf-8
#
# created by kpe on 10.01.2021 at 12:55 PM
#

from __future__ import division, absolute_import, print_function

import unittest
import os
import sys
import re
from datetime import datetime

import pyotp
import params as pp

from telerembash.cli import BotCli


class FromUser(pp.Params):
    id = 7411
    username = "username"


class Chat(pp.Params):
    id = 7411


class Message(pp.Params):
    from_user = FromUser()
    chat = Chat()
    date = datetime.now()
    text = ""
    
    async def answer(self, *args, **kwargs):
        print(*args, kwargs)


class MyTestCase(unittest.TestCase):
    totp = pyotp.TOTP(pyotp.random_base32())

    def test_cli_params(self):
        parser = BotCli.Params.to_argument_parser()
        args, _ = parser.parse_known_args(["init", 
                                           "--api-token", os.environ['TELEREM_API_TOKEN'],
                                           "--auth-secret", self.totp.secret,
                                           "--username", "username",
                                           "--user-id", "7411",
                                           "--config", "/tmp/telerem.config.yaml"
                                           ])
        bot = BotCli.from_params(BotCli.Params(args._get_kwargs()))
        bot.main()

    def test_start_params(self):
        parser = BotCli.Params.to_argument_parser()
        args, _ = parser.parse_known_args(["start",
                                           "--config", "/tmp/telerem.config.yaml",
                                           "--auth-secret", self.totp.secret
                                           ])
        
        from telerembash.bot import TeleRemBot, REX_AUTH, REX_DO
        cli = BotCli.from_params(BotCli.Params(args._get_kwargs()))
        params = TeleRemBot.Params.from_yaml_file(cli.params.config)
        bot = TeleRemBot.from_params(params)
        import asyncio

        def send_messages():
            msg = Message()
            msg.text = f"/auth {self.totp.now()}"
            
            print("send_messages")
            asyncio.run(bot.cmd_auth(msg, regexp_command=re.compile(REX_AUTH).match(msg.text)))

        asyncio.get_event_loop().call_later(3, lambda: asyncio.get_event_loop().stop())
        bot.main()
        send_messages()


if __name__ == '__main__':
    unittest.main()
