# coding=utf-8
#
# created by kpe on 09.01.2021 at 4:47 PM
#

from __future__ import division, absolute_import, print_function

import os
import re
import time
import subprocess
import logging

from aiogram import Bot, Dispatcher, executor, types, filters
import pyotp
import params as pp


log = logging.getLogger(__name__)

REX_AUTH = r'/auth\s+([0-9]{6})'
REX_DO = r'/do\s+([a-z0-9]+)\s?(.*)'


class TeleRemBot(pp.WithParams):
    class Params(pp.Params):
        bot_name = pp.Param("TeleRemBash", dtype=str, doc="The Bot Name (used in the OTP provisioning uri only)")
        api_token = pp.Param(None, dtype=str, doc="Telegram Bot API Token")
        auth_secret = pp.Param(None, dtype=str, doc="OPT Authenticator Secret (RFC 6238)")
        scripts_root = pp.Param("scripts", dtype=str, doc="scripts location")
        scripts_timeout = pp.Param(30, dtype=int, doc="execution timeout in seconds")
        username = pp.Param(None, dtype=str, doc="Username of the authorized user")
        user_id = pp.Param(None, dtype=int, doc="User IDs of the authorized user")

        @staticmethod
        def resolve_path(path):
            return path if path.startswith('/') else os.path.join(os.getcwd(), path)

        def get_scripts_root(self):
            return self.resolve_path(str(self.scripts_root))

    @property
    def params(self) -> Params:
        return self._params

    def _construct(self, *args, **kwargs):
        super(TeleRemBot, self)._construct(*args, **kwargs)
        if self.params.auth_secret is None:
            raise AttributeError("AUTH_SECRET not specified")
        self.totp = pyotp.TOTP(self.params.auth_secret)

        self.user_whitelist = [self.params.username]
        self.user_id_whitelist = [self.params.user_id]
        self.chat_id_whitelist = []

        # Initialize bot and dispatcher
        self.bot = Bot(token=self.params.api_token)
        self.dp = Dispatcher(self.bot)

        self.dp.register_message_handler(self.cmd_auth,
                                         filters.RegexpCommandsFilter(regexp_commands=[REX_AUTH]))
        self.dp.register_message_handler(self.cmd_do_execute,
                                         filters.RegexpCommandsFilter(regexp_commands=[REX_DO]))
        self.dp.register_message_handler(self.default_message_handler)

    def _precondition_fail(self, message: types.Message, field: str, value: str):
        log.warning(f"pre-condition fail: {field}:[{value}]: {message.to_python()}")

    def check_preconditions(self, message: types.Message, allow_unauthorized=False) -> bool:
        user_id = message.from_user.id
        user_name = message.from_user.username
        chat_id = message.chat.id

        if user_name not in self.user_whitelist:
            self._precondition_fail(message, 'user_name', user_name)
            return False
        if self.user_id_whitelist and user_id not in self.user_id_whitelist:
            self._precondition_fail(message, 'user_id', user_id)
            return False
        if not allow_unauthorized and chat_id not in self.chat_id_whitelist:
            self._precondition_fail(message, 'chat_id', user_id)
            return False
        if abs(int(message.date.timestamp()) - time.time()) > 10:
            self._precondition_fail(message, 'date', str(message.date.timestamp()))
            return False

        return True

    # @dp.message_handler(regex '/do\s+([0-9]+)')
    async def cmd_auth(self, message: types.Message, regexp_command: re.Match):
        if not self.check_preconditions(message, allow_unauthorized=True):
            return

        token = regexp_command.group(1)
        if not self.totp.verify(token):
            await message.answer("invalid")
            return

        username = message.from_user.username
        chat_id = message.chat.id
        for cid in self.chat_id_whitelist:   # notify current chats
            if cid != chat_id:
                await self.bot.send_message(chat_id, f"Farewell! Serving {username}!")
        self.chat_id_whitelist = [chat_id]

        await message.answer(f"Welcome, {username}!")
        await self.execute_script(message, 'welcome', '', silent_if_not_found=True)

    # @dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=[r'/do\s+([a-z0-9]+)\s?(.*)']))
    async def cmd_do_execute(self, message: types.Message, regexp_command: re.Match):
        if not self.check_preconditions(message):
            return

        cmd = regexp_command.group(1)
        params = regexp_command.group(2)
        await self.execute_script(message, cmd, params)

    async def execute_script(self, message: types.Message, cmd: str, params: str, silent_if_not_found=False):
        script_root = self.params.get_scripts_root()
        script_file = os.path.join(script_root, f"{cmd}")

        # auto append .sh suffix if there is no ext in the command
        if not os.path.exists(script_file) and len(cmd.split(".")) == 1 and os.path.exists(script_file + ".sh"):
            script_file += ".sh"
        else:
            if not silent_if_not_found:
                await message.reply(f"Can't do [{cmd}]")
            return

        try:
            out = subprocess.check_output([script_file] + params.split(),
                                          timeout=self.params.scripts_timeout,
                                          cwd=self.params.resolve_path(self.params.scripts_root),
                                          )
            await message.answer(out.decode('utf8'))
        except Exception as ex:
            log.warning(f"FAILED executing {script_file} {params.split()}: {ex}")
            await message.reply("failed")

    # @dp.message_handler()
    async def default_message_handler(self, message: types.Message):
        if not self.check_preconditions(message):
            return
        await message.reply("Don't understand")

    def main(self):
        import telerembash as tb
        print(f"TeleRemBash v{tb.__version__}")
        executor.start_polling(self.dp, skip_updates=True)
