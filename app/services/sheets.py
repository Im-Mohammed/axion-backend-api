"""
sheets.py
Google Sheets backup — initialised once at startup via init_sheets().
All writes are best-effort: failures are logged, never raised.
"""

import logging
from app.settings.config import get_settings

logger   = logging.getLogger("portfolio.sheets")
settings = get_settings()

_sheet    = None
SHEETS_OK = False


def init_sheets():
    global _sheet, SHEETS_OK

    if not settings.api.google_cred_path or not settings.api.sheet_name:
        logger.warning("Google Sheets not configured — backup disabled.")
        return

    try:
        import gspread
        from google.oauth2.service_account import Credentials  # modern library

        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds     = Credentials.from_service_account_file(
            settings.api.google_cred_path,
            scopes=scopes,           # correct param name for google-auth
        )
        client    = gspread.authorize(creds)
        _sheet    = client.open(settings.api.sheet_name).sheet1
        SHEETS_OK = True
        logger.info("Google Sheets backup connected.")

    except Exception as e:
        logger.warning(f"Google Sheets unavailable: {e}")


def sheet_append(row: list):
    if not SHEETS_OK or _sheet is None:
        return
    try:
        _sheet.append_row(row)
    except Exception as e:
        logger.warning(f"Sheet append failed: {e}")


def sheet_update_contact(email: str, github: str, linkedin: str):
    if not SHEETS_OK or _sheet is None:
        return
    try:
        from datetime import datetime
        rows = _sheet.get_all_records()
        for i, row in enumerate(rows, start=2):
            if row.get("email") == email:
                if github:
                    _sheet.update_cell(i, 12, f"https://github.com/{github}")
                if linkedin:
                    _sheet.update_cell(i, 13, f"https://linkedin.com/in/{linkedin}")
                _sheet.update_cell(i, 9, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                return
    except Exception as e:
        logger.warning(f"Sheet update_contact failed: {e}")
        
def get_all_from_sheets() -> list[dict]:
    """
    Read all visitor records from Google Sheets.
    Returns empty list if Sheets is unavailable or has no data.
    Called by admin_router to merge with Excel records.
    """
    if not SHEETS_OK or _sheet is None:
        return []
    try:
        return _sheet.get_all_records()
    except Exception as e:
        logger.warning(f"Sheet read failed: {e}")
        return []