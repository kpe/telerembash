# coding=utf-8
#
# created by kpe on 09.01.2021 at 4:47 PM
#

from __future__ import division, absolute_import, print_function

import os
import logging
import yaml
from enum import Enum, auto
import subprocess

from aiogram import Bot, Dispatcher, executor, types, filters
import pyotp

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


def _load_config(default_path='.config.yaml', env_key='BOT_CONFIG'):
    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'r') as f:
            config = yaml.safe_load(f.read())
            return config
    raise AttributeError(f"No config yaml found at:[{path}]")


config = _load_config()

totp = pyotp.TOTP(config['auth_secret'])

# Initialize bot and dispatcher
bot = Bot(token=config['api_token'])
dp = Dispatcher(bot)


class BotStates(Enum):
    NEW = auto()
    AWAITS_AUTH = auto()
    READY = auto()


class BotState:
    state = BotStates.NEW
    user_id = None
    user_name = None
    chat_id = None


state = BotState()


def _precondition_fail(message: types.Message, field: str, value: str):
    log.debug(f"msg:[{message.to_python()}]")
    log.warning(f"pre-condition fail: ${field}:[{value}]")


def check_preconditions(message: types.Message) -> bool:
    global state

    user_id = message.from_user.id
    user_name = message.from_user.username
    chat_id = message.chat.id
    chat_type = message.chat.type

    if user_name not in config['users']:
        _precondition_fail(message, 'user_name', user_name)
        return False
    if 'user_ids' in config and user_id not in config['user_ids']:
        _precondition_fail(message, 'user_id', user_id)
        return False
    if chat_type != 'private':
        _precondition_fail(message, 'chat_type', chat_type)
        return False

    if state.state not in [BotStates.NEW, BotStates.AWAITS_AUTH]:
        if chat_id != state.chat_id:
            _precondition_fail(message, 'chat_id', chat_id)
            return False

    return True


@dp.message_handler(commands=['start', 'auth'])
async def start(message: types.Message):
    global state

    if not check_preconditions(message):
        return

    state = BotState()
    state.state = BotStates.AWAITS_AUTH
    await message.reply("auth first")


async def on_auth_key(message: types.Message, callback=None):
    if not totp.verify(message.text):
        await message.answer("invalid")
        return

    state.state = BotStates.READY
    state.user_id = message.from_user.id
    state.user_name = message.from_user.username
    state.chat_id = message.chat.id

    if callback is not None:
        await callback(message)


async def on_auth_ok(message: types.Message):
    await message.answer("Welcome, Master!")
    await execute_script(message, 'welcome', '')


@dp.message_handler(filters.RegexpCommandsFilter(regexp_commands=[r'/do\s+([a-z0-9]+)\s?(.*)']))
async def execute(message: types.Message, regexp_command):
    cmd = regexp_command.group(1)
    params = regexp_command.group(2)
    print("do:", regexp_command, (cmd, params), message.to_python())
    await execute_script(message, cmd, params)


async def execute_script(message: types.Message, cmd: str, params: str):
    global config

    script_root = os.getcwd()
    script_path = f"{cmd}"
    if 'scripts' in config and cmd in config['scripts']:
        script_path = config['scripts'][cmd]
    else:
        await message.reply(f"Can't do [{cmd}]")
    if 'scripts_root' in config:
        script_root = os.path.join(script_root, config['scripts_root'])

    script_file = os.path.join(script_root, script_path)
    if not os.path.exists(script_file) and not script_path.endswith(".sh"):
        script_file = os.path.join(script_root, script_path + ".sh")
    if not os.path.exists(script_file):
        await message.reply(f"Can't do [{cmd}]")
        return

    try:
        out = subprocess.check_output([script_file] + params.split(), timeout=5)
        await message.answer(out.decode('utf8'))
    except Exception as ex:
        print(ex)
        await message.reply("failed")


@dp.message_handler()
async def message_handler(message: types.Message):
    global state
    if not check_preconditions(message):
        return

    if state.state == BotStates.NEW:
        await message.reply("auth first")
    if state.state == BotStates.AWAITS_AUTH:
        await on_auth_key(message, on_auth_ok)
    else:
        if state.chat_id == message.chat.id:
            await message.reply("Don't understand")


def print_totp_qr():
    import sys
    import subprocess
    uri = totp.provisioning_uri(name='user', issuer_name='TeleRemBash')
    sys.stdout.write(subprocess.check_output(['qrc', uri]).decode('utf8'))


if __name__ == '__main__':
    import telerembash as tb
    print(f"TeleRemBash v{tb.__version__}")

    print_totp_qr()
    executor.start_polling(dp, skip_updates=True)
