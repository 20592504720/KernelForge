"""Restricted HTTPS metadata requests: validate before every redirect."""
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


class MetadataURLerror(ValueError):
    pass


def require_https_host(url, host, *, allow_query=False):
    try:
        if not isinstance(url, str) or any(ord(c) < 33 or c == "\\" for c in url):
            raise ValueError("invalid URL")
        p = urlsplit(url)
        if (p.scheme != "https" or p.hostname != host or p.port not in (None, 443)
                or p.username is not None or p.password is not None or p.fragment
                or (p.query and not allow_query)):
            raise ValueError("unexpected origin")
    except ValueError as exc:
        raise MetadataURLerror("metadata request outside permitted authenticated HTTPS origin") from exc
    return p


class _OriginRedirect(HTTPRedirectHandler):
    def __init__(self, host, allow_query):
        super().__init__()
        self.host = host
        self.allow_query = allow_query

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require_https_host(newurl, self.host, allow_query=self.allow_query)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_metadata(request, *, host, timeout, allow_query=False):
    require_https_host(request.full_url, host, allow_query=allow_query)
    opener = build_opener(_OriginRedirect(host, allow_query))
    response = opener.open(request, timeout=timeout)
    try:
        require_https_host(response.geturl(), host, allow_query=allow_query)
    except BaseException:
        response.close()
        raise
    return response


def read_bounded(response, limit):
    data = response.read(limit + 1)
    if len(data) > limit:
        raise MetadataURLerror("metadata response exceeds byte budget")
    return data
