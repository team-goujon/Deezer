
class DeezerServiceError(Exception):
    """Base class for exceptions in DeezerService."""
    def __init__(self, message: str):
        self.message = message
    pass
