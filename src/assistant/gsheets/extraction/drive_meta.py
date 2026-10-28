from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


def get_modified_time(spreadsheet_id: str, credentials_path: str) -> str:
    creds = Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    meta = drive.files().get(
        fileId=spreadsheet_id,
        fields="modifiedTime",
    ).execute()

    return meta["modifiedTime"]