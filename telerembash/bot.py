# coding=utf-8
#
# created by kpe on 09.01.2021 at 4:47 PM
#

from __future__ import division, absolute_import, print_function

import os
import logging
import yaml
from enum import Enum, auto
from collections import defaultdict
import subprocess

from aiogram import Bot, Dispatcher, executor, types, filters
import pyotp
import params as pp


log = logging.getLogger(__name__)

db: Dispatcher = None


class SessionState(Enum):
    NEW = auto()
    AWAITS_AUTH = auto()
    READY = auto()


class TeleRemBot(pp.WithParams):
    class Params(pp.Params):
        bot_name = pp.Param("TeleRemBash", dtype=str, doc="The Bot Name (used in the OTP provisioning uri only)")
        api_token = pp.Param(None, dtype=str, doc="Telegram Bot API Token")
        auth_secret = pp.Param(None, dtype=str, doc="OPT Authenticator Secret (RFC 6238)")
        scripts_root = pp.Param("scripts", dtype=str, doc="scripts location")
        username = pp.Param(None, dtype=str, doc="Username of the authorized user")
        user_id = pp.Param(None, dtype=int, doc="User IDs of the authorized user")
        
        def to_abs_path(self, rel_path):
            return rel_path if rel_path.startswith('/') else os.path.join(os.getcwd(), rel_path)
        
    @property
    def params(self) -> Params:
        return self._params

    def _construct(self, *args, **kwargs):
        super(TeleRemBot, self)._construct(*args, **kwargs)
        if self.params.auth_secret is None:
            raise AttributeError("AUTH_SECRET not specified")
        self.totp = pyotp.TOTP(self.params.auth_secret)
        
        self.user_permits = [self.params.username]
        self.user_id_permits = [self.params.user_id]
        
        # Initialize bot and dispatcher
        self.bot = Bot(token=self.params.api_token)
        self.dp = Dispatcher(self.bot)
        self.chat2state = defaultdict(lambda: SessionState.NEW)   # chat_id to state
        
        self.dp.register_message_handler(self.start, commands=['start', 'auth'])
        self.dp.register_message_handler(self.execute,
                                         filters.RegexpCommandsFilter(regexp_commands=[r'/do\s+([a-z0-9]+)\s?(.*)']))
        self.dp.register_message_handler(self.message_handler)

    def _precondition_fail(self, message: types.Message, field: str, value: str):
        log.debug(f"msg:[{message.to_python()}]")
        log.warning(f"pre-condition fail: ${field}:[{value}]")

    def check_preconditions(self, message: types.Message) -> bool:
        user_id = message.from_user.id
        user_name = message.from_user.username
        chat_id = message.chat.id
        chat_type = message.chat.type

        if user_name not in self.user_permits:
            self._precondition_fail(message, 'user_name', user_name)
            return False
        if self.user_id_permits and user_id not in self.user_id_permits:
            self._precondition_fail(message, 'user_id', user_id)
            return False
        if chat_type != 'private':
            self._precondition_fail(message, 'chat_type', chat_type)
            return False
        return True

    # @dp.message_handler(commands=['start', 'auth'])
    async def start(self, message: types.Message):
        if not self.check_preconditions(message):
            return

        self.chat2state[message.chat.id] = SessionState.AWAITS_AUTH
        await message.reply("auth first")

    async def on_auth_key(self, message: types.Message, callback=None):
        chat_id = message.chat.id

        if not self.totp.verify(message.text):
            await message.answer("invalid")
            if chat_id in self.chat2state:
                del self.chat2state[chat_id]
            return
    
        self.chat2state[chat_id] = SessionState.READY

        if callback is not None:
            await callback(message)

    async def on_auth_ok(self, message: types.Message):
        await message.answer("Welcome, Master!")
        await self.execute_script(message, 'welcome', '')

    # @dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=[r'/do\s+([a-z0-9]+)\s?(.*)']))
    async def execute(self, message: types.Message, regexp_command):
        cmd = regexp_command.group(1)
        params = regexp_command.group(2)
        print("do:", regexp_command, (cmd, params), message.to_python())
        await self.execute_script(message, cmd, params)

    async def execute_script(self, message: types.Message, cmd: str, params: str):
        script_root = self.params.scripts_root
        script_file = os.path.join(script_root, f"{cmd}")
        script_file = self.params.to_abs_path(script_file)

        if not os.path.exists(script_file) and not script_file.endswith(".sh"):
            script_file = self.params.to_abs_path(os.path.join(script_root, f"{cmd}.sh"))
        if not os.path.exists(script_file):
            await message.reply(f"Can't do [{cmd}]")
            return
    
        try:
            out = subprocess.check_output([script_file] + params.split(), timeout=5)
            await message.answer(out.decode('utf8'))
        except Exception as ex:
            print(ex)
            await message.reply("failed")

    # @dp.message_handler()
    async def message_handler(self, message: types.Message):
        if not self.check_preconditions(message):
            return
        chat_id = message.chat.id

        if chat_id not in self.chat2state:
            await message.reply("auth first")
        if self.chat2state[chat_id] == SessionState.AWAITS_AUTH:
            await self.on_auth_key(message, self.on_auth_ok)
        else:
            await message.reply("Don't understand")

    def main(self):
        import telerembash as tb
        print(f"TeleRemBash v{tb.__version__}")
        executor.start_polling(self.dp, skip_updates=True)
