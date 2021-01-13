TeleRemBash
===========

``TeleRemBash`` is a `Telegram`_ Remote Bash `Bot`_ for executing
scripts on the remote system, baked with `TOTP`_ Authentication for
easy and secure setup.

To keep things simple ``TeleRamBash`` supports a single Telegram user
after `TOTP`_ Authenticationw to execute a pre-defined (bash) script
by sending a command to the Bot in a Telegram chat.

Usage
-----
First create a configuration for your Telegram Bot instance by specifying
the Bot's ``API_TOKEN`` and the Telegram username of the whitelisted user:

.. code:: bash

   python -m telerembash init --api_token API_TOKEN --username USERNAME

this should create a ``telerem.config.yaml`` in the current directory
and output a QR Code you can scan in your TOTP Authenticator App (i.e.
`Google Authenticator`_, `andOTP`_, etc).

for initialize
After obtaining a Telegram ``API_TOKEN`` for you bot

NEWS
----
 - **09.Jan.2021** - initial

LICENSE
-------

MIT. See `License File <https://github.com/kpe/telerembash/blob/master/LICENSE.txt>`_.


Resources
---------

- `Telegram`_ - Telegram BOT API
- `PyOTP`_ - The Python One-Time Password Library
- `python-qrcode`_ - QR code generator for text terminals

.. _`python-qrcode`: https://github.com/lincolnloop/python-qrcode
.. _`PyOTP`: https://github.com/pyauth/pyotp
.. _`TOTP`: https://en.wikipedia.org/wiki/Time-based_One-Time_Password
.. _`Telegram`: https://core.telegram.org/api
.. _`Bot`: https://core.telegram.org/bots
.. _`Google Authenticator`: https://play.google.com/store/apps/details?id=org.shadowice.flocke.andotp
.. _`andOTP`: https://play.google.com/store/apps/details?id=org.shadowice.flocke.andotp
