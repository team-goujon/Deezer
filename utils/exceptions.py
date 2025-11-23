
class DeezerServiceError(Exception):
    """Base class for exceptions in DeezerService."""
    def __init__(self, message: str):
        self.message = message
    pass

class DeezerAPIError(Exception):
    """Base class for exceptions in DeezerAPI."""
    def __init__(self, message: str):
        self.message = message
    pass
  
class LoginException(Exception):
	def __init__(self, message):
		super().__init__(message)

class ConfigException(Exception):
	def __init__(self, message):
		super().__init__(message)
