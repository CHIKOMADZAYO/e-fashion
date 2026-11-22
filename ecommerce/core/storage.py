import os
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.files.storage import Storage
from django.core.files.base import File


class VercelBlobStorage(Storage):
    """Custom Django storage backend for Vercel Blob."""

    def __init__(self):
        self.token = settings.VERCEL_BLOB_READ_WRITE_TOKEN
        self.store_id = settings.VERCEL_BLOB_STORE_ID
        self.base_url = f"https://{self.store_id}.blob.vercel-storage.com"

    def _normalize_name(self, name):
        """Ensure forward slashes for Vercel Blob paths."""
        return name.replace("\\", "/")

    def _save(self, name, content):
        name = self._normalize_name(name)
        url = f"{self.base_url}/{quote(name)}"

        content.seek(0)
        data = content.read()

        content_type = getattr(content, 'content_type', None) or 'application/octet-stream'

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": content_type,
            "x-vercel-blob-content-type": content_type,
        }

        response = requests.put(url, data=data, headers=headers, timeout=60)

        if response.status_code not in (200, 201):
            raise IOError(
                f"Vercel Blob upload failed ({response.status_code}): {response.text}"
            )

        return name

    def _open(self, name, mode="rb"):
        name = self._normalize_name(name)
        url = f"{self.base_url}/{quote(name)}"

        response = requests.get(url, headers={"Authorization": f"Bearer {self.token}"}, timeout=60)
        response.raise_for_status()

        return File(response.content, name=name)

    def url(self, name):
        name = self._normalize_name(name)
        return f"{self.base_url}/{quote(name)}"

    def exists(self, name):
        name = self._normalize_name(name)
        url = f"{self.base_url}/{quote(name)}"
        try:
            response = requests.head(
                url, headers={"Authorization": f"Bearer {self.token}"}, timeout=30
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def delete(self, name):
        name = self._normalize_name(name)
        url = f"{self.base_url}/{quote(name)}"
        try:
            requests.delete(
                url, headers={"Authorization": f"Bearer {self.token}"}, timeout=30
            )
        except requests.RequestException:
            pass

    def size(self, name):
        name = self._normalize_name(name)
        url = f"{self.base_url}/{quote(name)}"
        try:
            response = requests.head(
                url, headers={"Authorization": f"Bearer {self.token}"}, timeout=30
            )
            if response.status_code == 200:
                return int(response.headers.get("content-length", 0))
        except requests.RequestException:
            pass
        return 0

    def get_available_name(self, name, max_length=None):
        """Vercel Blob overwrites by default; return name as-is."""
        return name
