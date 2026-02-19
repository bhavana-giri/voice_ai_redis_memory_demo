"""Google Calendar client using Google Calendar API (OAuth)."""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Read-only scope for calendar
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class CalendarClient:
    """Read-only Google Calendar client using Google Calendar API."""

    def __init__(self, timezone: str = "Asia/Kolkata"):
        self.timezone = ZoneInfo(timezone)
        self._service = None
        self._creds = None

    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth credentials."""
        if self._creds and self._creds.valid:
            return self._creds

        # Check for saved token
        token_path = "token.json"
        creds_path = "credentials.json"

        if os.path.exists(token_path):
            self._creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Refresh or get new credentials
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                self._creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    raise FileNotFoundError(
                        "credentials.json not found. Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                self._creds = flow.run_local_server(port=0)

            # Save for next time
            with open(token_path, "w") as token:
                token.write(self._creds.to_json())

        return self._creds

    def _get_service(self):
        """Get or create the Calendar API service."""
        if not self._service:
            creds = self._get_credentials()
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def _parse_event(self, event: Dict) -> Dict[str, Any]:
        """Parse a Google Calendar event into a dict."""
        start = event.get("start", {})
        end = event.get("end", {})

        # Handle all-day vs timed events
        if "dateTime" in start:
            start_dt = datetime.fromisoformat(start["dateTime"])
            is_all_day = False
        elif "date" in start:
            start_dt = datetime.strptime(start["date"], "%Y-%m-%d").date()
            is_all_day = True
        else:
            start_dt = None
            is_all_day = False

        if "dateTime" in end:
            end_dt = datetime.fromisoformat(end["dateTime"])
        elif "date" in end:
            end_dt = datetime.strptime(end["date"], "%Y-%m-%d").date()
        else:
            end_dt = None

        return {
            "summary": event.get("summary", "No title"),
            "start": start_dt,
            "end": end_dt,
            "location": event.get("location"),
            "description": event.get("description"),
            "is_all_day": is_all_day,
        }

    def get_events(self, days_ahead: int = 7, days_back: int = 0) -> List[Dict[str, Any]]:
        """Get events within a date range."""
        service = self._get_service()
        now = datetime.now(self.timezone)

        time_min = (now - timedelta(days=days_back)).isoformat()
        time_max = (now + timedelta(days=days_ahead + 1)).isoformat()

        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for event in events_result.get("items", []):
            events.append(self._parse_event(event))

        return events

    def get_today_events(self) -> List[Dict[str, Any]]:
        """Get today's events."""
        return self.get_events(days_ahead=0, days_back=0)

    def get_upcoming_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get next N upcoming events."""
        events = self.get_events(days_ahead=30)
        now = datetime.now(self.timezone)
        
        # Filter to future events only
        future_events = []
        for e in events:
            if isinstance(e["start"], datetime):
                if e["start"] > now:
                    future_events.append(e)
            else:  # date object
                if e["start"] >= now.date():
                    future_events.append(e)
        
        return future_events[:limit]

    def format_events_for_context(self, events: List[Dict[str, Any]]) -> str:
        """Format events as a string for LLM context."""
        if not events:
            return "No events found."

        lines = []
        for e in events:
            if e["is_all_day"]:
                time_str = f"{e['start'].strftime('%A, %B %d')} (all day)"
            else:
                time_str = e["start"].strftime("%A, %B %d at %I:%M %p")
            
            line = f"- {e['summary']}: {time_str}"
            if e["location"]:
                line += f" at {e['location']}"
            lines.append(line)

        return "\n".join(lines)

    def get_calendar_context(self) -> str:
        """Get a summary of calendar for LLM context."""
        today = self.get_today_events()
        upcoming = self.get_upcoming_events(limit=5)

        parts = []
        if today:
            parts.append(f"Today's events:\n{self.format_events_for_context(today)}")
        if upcoming:
            parts.append(f"Upcoming events:\n{self.format_events_for_context(upcoming)}")

        return "\n\n".join(parts) if parts else "No upcoming calendar events."

