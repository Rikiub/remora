import re
from http.cookies import Morsel, SimpleCookie


class LenientSimpleCookie(SimpleCookie):
    """More lenient version of http.cookies.SimpleCookie

    Copied directly from yt-dlp implementation. Mostly to avoid depend of yt-dlp.
    """

    # From https://github.com/python/cpython/blob/v3.10.7/Lib/http/cookies.py
    # We use Morsel's legal key chars to avoid errors on setting values
    _LEGAL_KEY_CHARS = r"\w\d" + re.escape("!#$%&'*+-.:^_`|~")
    _LEGAL_VALUE_CHARS = _LEGAL_KEY_CHARS + re.escape("(),/<=>?@[]{}")
    _LEGAL_KEY_RE = re.compile(rf"[{_LEGAL_KEY_CHARS}]+", re.ASCII)

    _RESERVED = frozenset(
        {
            "expires",
            "path",
            "comment",
            "domain",
            "max-age",
            "secure",
            "httponly",
            "version",
            "samesite",
        }
    )

    _FLAGS = frozenset({"secure", "httponly"})

    # Added 'bad' group to catch the remaining value
    _COOKIE_PATTERN = re.compile(
        r"""
        [ ]*                           # Optional whitespace at start of cookie
        (?P<key>                       # Start of group 'key'
        [^ =;]+                        # Match almost anything here for now and validate later
        )                              # End of group 'key'
        (                              # Optional group: there may not be a value.
        [ ]*=[ ]*                        # Equal Sign
        (                                # Start of potential value
        (?P<val>                           # Start of group 'val'
        "(?:[^\\"]|\\.)*"                    # Any doublequoted string
        |                                    # or
        \w{3},\ [\w\d -]{9,11}\ [\d:]{8}\ GMT  # Special case for "expires" attr
        |                                    # or
        ["""
        + _LEGAL_VALUE_CHARS
        + r"""]*     # Any word or empty string
        )                                  # End of group 'val'
        |                                  # or
        (?P<bad>(?:\\;|[^;])*?)            # 'bad' group fallback for invalid values
        )                                # End of potential value
        )?                             # End of optional value group
        [ ]*                            # Any number of spaces.
        ([ ]+|;|$)                      # Ending either at space, semicolon, or EOS.
        """,
        re.ASCII | re.VERBOSE,
    )

    # http.cookies.Morsel raises on values w/ control characters in Python 3.14.3+ & 3.13.12+
    # Ref: https://github.com/python/cpython/issues/143919
    _CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1F\x7F]")

    def load(self, rawdata):
        # Workaround for https://github.com/yt-dlp/yt-dlp/issues/4776
        if not isinstance(rawdata, str):
            return super().load(rawdata)

        morsel = None
        for match in self._COOKIE_PATTERN.finditer(rawdata):
            if match.group("bad"):
                morsel = None
                continue

            key, value = match.group("key", "val")
            if not self._LEGAL_KEY_RE.fullmatch(key):
                morsel = None
                continue

            is_attribute = False
            if key.startswith("$"):
                key = key[1:]
                is_attribute = True

            lower_key = key.lower()
            if lower_key in self._RESERVED:
                if morsel is None:
                    continue

                if value is None:
                    if lower_key not in self._FLAGS:
                        morsel = None
                        continue
                    value = True
                else:
                    value, _ = self.value_decode(value)
                    # Guard against control characters in quoted attribute values
                    if self._CONTROL_CHARACTER_RE.search(value):
                        # While discarding the entire morsel is not very lenient,
                        # it's better than http.cookies.Morsel raising a CookieError
                        # and it's probably better to err on the side of caution
                        self.pop(morsel.key, None)
                        morsel = None
                        continue

                morsel[key] = value

            elif is_attribute:
                morsel = None

            elif value is not None:
                morsel = self.get(key, Morsel())
                real_value, coded_value = self.value_decode(value)
                # Guard against control characters in quoted cookie values
                if self._CONTROL_CHARACTER_RE.search(real_value):
                    morsel = None
                    continue
                morsel.set(key, real_value, coded_value)
                self[key] = morsel

            else:
                morsel = None
