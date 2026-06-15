"""
Google Drive integration using service account credentials.
Manages exactly 2 resume files: resume_base + one dated copy.
"""

import io
import logging
from config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_SERVICE_ACCOUNT_JSON

log = logging.getLogger(__name__)

def _get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_info(
        GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def _find_file(service, name: str) -> str | None:
    """Return file ID if found in the resume folder, else None."""
    q = f"name='{name}.txt' and '{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed=false"
    results = service.files().list(q=q, fields="files(id,name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def download_resume(name: str = "resume_base") -> str:
    """Download resume text from Drive. Raises if not found."""
    from googleapiclient.http import MediaIoBaseDownload

    service = _get_drive_service()
    file_id = _find_file(service, name)

    if not file_id:
        raise FileNotFoundError(
            f"'{name}.txt' not found in Drive folder {GOOGLE_DRIVE_FOLDER_ID}.\n"
            "Please upload your base resume first (see SETUP.md)."
        )

    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    text = buf.getvalue().decode("utf-8")
    log.info(f"Downloaded {name}.txt ({len(text)} chars)")
    return text


def upload_resume(text: str, name: str) -> str:
    """Upload or overwrite a resume file in Drive. Returns file ID."""
    from googleapiclient.http import MediaIoBaseUpload

    service = _get_drive_service()
    buf = io.BytesIO(text.encode("utf-8"))
    media = MediaIoBaseUpload(buf, mimetype="text/plain")

    existing_id = _find_file(service, name)

    if existing_id:
        service.files().update(fileId=existing_id, media_body=media).execute()
        log.info(f"Updated {name}.txt in Drive")
        return existing_id
    else:
        meta = {
            "name": f"{name}.txt",
            "parents": [GOOGLE_DRIVE_FOLDER_ID]
        }
        f = service.files().create(body=meta, media_body=media, fields="id").execute()
        log.info(f"Created {name}.txt in Drive (id: {f['id']})")
        return f["id"]


def delete_old_dated_resume():
    """Delete any existing dated resume (resume_YYYY-MM-DD) to keep only 2 files total."""
    import re
    service = _get_drive_service()

    q = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed=false and name contains 'resume_'"
    results = service.files().list(q=q, fields="files(id,name)").execute()

    for f in results.get("files", []):
        if re.match(r"resume_\d{4}-\d{2}-\d{2}\.txt", f["name"]):
            service.files().delete(fileId=f["id"]).execute()
            log.info(f"Deleted old dated file: {f['name']}")
