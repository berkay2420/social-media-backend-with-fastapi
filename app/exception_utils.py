from datetime import datetime, timezone
from fastapi import HTTPException, status

USER_NOT_FOUND = "USER_001"
INVALID_USER_ID_FORMAT = "USER_002"
PERMISSION_DENIED = "USER_003"
INVALID_PAGINATION = "USER_004"

# GENEL ERROR CODES
INTERNAL_SERVER_ERROR = "SYS_500"

# POST ERROR CODES
POST_INVALID_ID_FORMAT = "POST_001"
POST_NOT_FOUND = "POST_002"
POST_INVALID_FILE_TYPE = "POST_003"
POST_FILE_TOO_LARGE = "POST_004"
POST_UPLOAD_FAILED = "POST_005"
POST_ALREADY_UPVOTED = "POST_006"
UPVOTE_NOT_FOUND = "POST_007"
POST_INVALID_SORT_KEY = "POST_008"

#AUTH ERROR CODES
AUTH_EMAIL_OR_USERNAME_EXISTS = "AUTH_001"
AUTH_INVALID_CREDENTIALS = "AUTH_002"
AUTH_INVALID_TOKEN = "AUTH_003"
AUTH_TOKEN_EXPIRED = "AUTH_004"
AUTH_USER_NOT_FOUND_FOR_TOKEN = "AUTH_005"
AUTH_TOKEN_MISMATCH =  "AUTH_001"


class AppException(HTTPException):
    """Custom app exception with error code"""
    
    def __init__(
        self,
        detail: str,
        error_code: str,
        status_code: int,
        headers: dict = None
    ):
        self.error_code = error_code
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers=headers
        )