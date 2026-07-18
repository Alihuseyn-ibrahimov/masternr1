"""Meta webhook imza yoxlanışı (X-Hub-Signature-256)."""

import hashlib
import hmac


def verify_signature(app_secret: str, body: bytes, header: str | None) -> bool:
    """Meta-nın `X-Hub-Signature-256` başlığını gövdə ilə tutuşdurur.

    header formatı: "sha256=<hexdigest>". app_secret boşdursa (konfiqurasiya
    edilməyibsə) yoxlama keçilmiş sayılmır → False.
    """
    if not app_secret or not header:
        return False
    if not header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    received = header.split("=", 1)[1]
    return hmac.compare_digest(expected, received)
