"""Domain errors. The API layer converts these to HTTP responses (cline.md rule 13: never swallow)."""


class AppError(Exception):
    """Base class so callers can catch our domain errors specifically."""


class ItemNotFoundError(AppError):
    """Raised when an item id does not exist in the local store."""


class AirtableError(AppError):
    """Raised when the third-party mirror could not be completed right now."""
