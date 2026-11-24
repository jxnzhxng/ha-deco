"""Keep Deco session tokens out of the Home Assistant log.

Request URLs carry the session token (``;stok=<token>``, or ``id=<token>`` on
legacy firmware), and aiohttp errors quote the URL. A filter on every logger of
this integration removes the token before a record is written.
"""

import logging
import pkgutil
import re

_SECRET_PATTERN = re.compile(r"(stok=|[?&]id=)[^/?&'\"\s]+")
_EXCEPTION_FORMATTER = logging.Formatter()


def redact(text: str) -> str:
    """Return text without Deco session tokens."""
    return _SECRET_PATTERN.sub(r"\1REDACTED", text)


class SessionTokenFilter(logging.Filter):
    """Redact session tokens in the message and the traceback of a record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # A broken log call must still reach the log.
            return True
        redacted = redact(message)
        if redacted != message:
            record.msg = redacted
            record.args = None
        if record.exc_info and not record.exc_text:
            record.exc_text = _EXCEPTION_FORMATTER.formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = redact(record.exc_text)
        return True


def install(package_name: str, package_path) -> None:
    """Add the filter to the logger of the package and of each of its modules."""
    names = [package_name, f"{package_name}.__init__"] + [
        f"{package_name}.{module.name}" for module in pkgutil.iter_modules(package_path)
    ]
    for name in names:
        logger = logging.getLogger(name)
        if not any(isinstance(f, SessionTokenFilter) for f in logger.filters):
            logger.addFilter(SessionTokenFilter())
