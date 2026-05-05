class SynologyError(Exception):
    pass


class SynologyConnectionError(SynologyError):
    pass


class SynologyAuthError(SynologyError):
    pass


class SynologyApiError(SynologyError):
    pass