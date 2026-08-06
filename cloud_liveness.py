"""
Pluggable liveness-verification interface for a licensed cloud SDK
(integration layer only, not a real vendor engine).

Supports optional third-party cloud liveness checks (e.g., iProov, FaceTec,
Onfido) while providing a NullCloudProvider default so the system works out
of the box without any cloud configuration.
"""

from abc import ABC, abstractmethod
import os
import cv2
import requests


class CloudLivenessProvider(ABC):
    """Abstract base class for cloud-based liveness verification providers."""

    @abstractmethod
    def verify(self, face_image_bgr) -> dict:
        """
        Verifies liveness of a face crop against a cloud provider API.

        Returns:
            dict: At minimum {"is_live": bool or None, "confidence": float or None, "provider": str}
                  Where is_live=None indicates the provider is unconfigured or unavailable.
        """
        pass


class NullCloudProvider(CloudLivenessProvider):
    """
    Default no-op cloud provider. Returns {"is_live": None, "confidence": None,
    "provider": "none"} meaning "not configured", so the local liveness pipeline
    operates identically out of the box.
    """

    def verify(self, face_image_bgr) -> dict:
        return {
            "is_live": None,
            "confidence": None,
            "provider": "none",
        }


class GenericCloudProvider(CloudLivenessProvider):
    """
    Generic HTTP-based example cloud liveness provider.

    NOTE ON VENDOR ADAPTATION:
    This is a generic template. To actually use a commercial vendor SDK such as
    iProov, FaceTec, or Onfido, the developer must:
      1. Sign up for a business account with that vendor.
      2. Obtain the vendor-specific API documentation and credentials.
      3. Adjust the HTTP request headers, payload format (e.g., base64, multipart form),
         and JSON response parsing below to match that specific vendor's real API schema.
    """

    def __init__(self, api_key=None, endpoint_url=None, timeout_seconds=3.0):
        # Reads from environment variables if not passed explicitly — never hardcode keys.
        self.api_key = api_key or os.environ.get("CLOUD_LIVENESS_API_KEY", "")
        self.endpoint_url = endpoint_url or os.environ.get("CLOUD_LIVENESS_ENDPOINT", "")
        self.timeout_seconds = timeout_seconds

    def verify(self, face_image_bgr) -> dict:
        if not self.api_key or not self.endpoint_url or face_image_bgr is None or face_image_bgr.size == 0:
            return {
                "is_live": None,
                "confidence": None,
                "provider": "generic",
            }

        try:
            # Encode face crop to JPEG bytes for HTTP POST
            success, encoded_img = cv2.imencode(".jpg", face_image_bgr)
            if not success:
                return {"is_live": None, "confidence": None, "provider": "generic"}

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "SmartAttendanceSystem/1.0",
            }
            files = {
                "image": ("face.jpg", encoded_img.tobytes(), "image/jpeg"),
            }

            # Wrap all network calls in try/except so a failure never crashes the local pipeline
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                files=files,
                timeout=self.timeout_seconds,
            )

            if response.status_code == 200:
                data = response.json()
                # Parse generic response dictionary; vendors will have their own field names
                is_live = data.get("is_live", data.get("liveness", None))
                confidence = float(data.get("confidence", data.get("score", 0.0)))
                return {
                    "is_live": bool(is_live) if is_live is not None else None,
                    "confidence": confidence,
                    "provider": "generic",
                }
            else:
                return {
                    "is_live": None,
                    "confidence": None,
                    "provider": "generic",
                }

        except Exception:
            # Any network timeout, connection error, or JSON decode failure returns None
            return {
                "is_live": None,
                "confidence": None,
                "provider": "generic",
            }
