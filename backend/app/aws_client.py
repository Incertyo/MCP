from __future__ import annotations

from typing import Any

from .config import settings

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover
    boto3 = None
    BotoCoreError = ClientError = Exception


class AwsValidationError(RuntimeError):
    pass


def validate_real_account(access_key_id: str, secret_access_key: str, session_token: str, region: str) -> dict[str, Any]:
    if boto3 is None:
        raise AwsValidationError(
            "boto3 is not installed. Install backend dependencies (run `pip install -r backend/requirements.txt` from the repo root, "
            "or `pip install -r requirements.txt` from `backend/`) and restart the backend."
        )
    if not access_key_id or not secret_access_key:
        raise AwsValidationError("Real AWS mode requires access key ID and secret access key.")

    try:
        session = boto3.session.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token or None,
            region_name=region or settings.dynamodb_region,
        )
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return {
            "account_id": identity.get("Account", ""),
            "arn": identity.get("Arn", ""),
            "user_id": identity.get("UserId", ""),
        }
    except (BotoCoreError, ClientError) as exc:
        raise AwsValidationError("AWS credential validation failed. Check the account ID, access key, secret key, session token, and region.") from exc
