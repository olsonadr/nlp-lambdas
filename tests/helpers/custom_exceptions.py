# Some custom exceptions to help categorize testing
class JsonException(Exception): pass
class SamOutputException(Exception): pass
class SamExecutionException(Exception): pass
class StartApiTimeoutException(Exception): pass
class InternalServerException(Exception): pass