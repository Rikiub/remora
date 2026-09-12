from remora.models import Cookie, Cookies

name = "id"
value = "1"
domain = ".example.com"
path = "/"
expires = 1999999

http_cookies = f"{name}={value}; Domain={domain}; Path={path}; Expires={expires}"
data_cookies = Cookie(
    name=name,
    value=value,
    domain=domain,
    path=path,
    expires=expires,
)


def test_from_http_cookies():
    parsed = Cookies.from_cookie_header(http_cookies)
    assert parsed[0] == data_cookies


def test_to_http_cookies():
    parsed = Cookies([data_cookies])
    parsed = parsed.to_cookie_header()
    assert parsed == http_cookies
