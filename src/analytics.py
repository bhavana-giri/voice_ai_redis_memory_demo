"""Analytics and insights for voice journal entries."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from collections import Counter
import redis
import json
from dotenv import load_dotenv

load_dotenv()


class JournalAnalytics:
    """Analytics and insights for voice journal entries."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.client = redis.from_url(self.redis_url)
        self.entries_prefix = "voice_journal:entries"
        self.audio_prefix = "voice_journal:audio"
    
    def _get_all_user_entries(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all entries for a user."""
        entry_ids = self.client.zrange(
            f"{self.entries_prefix}:user:{user_id}", 0, -1
        )
        entries = []
        for eid in entry_ids:
            if isinstance(eid, bytes):
                eid = eid.decode()
            data = self.client.get(f"{self.entries_prefix}:{eid}")
            if data:
                entries.append(json.loads(data))
        return entries
    
    def get_entry_frequency(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, int]:
        """
        Get entry frequency per day for the last N days.
        
        Returns:
            Dict mapping date strings to entry counts
        """
        entries = self._get_all_user_entries(user_id)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        frequency = Counter()
        for entry in entries:
            created_at = datetime.fromisoformat(
                entry["created_at"].replace("Z", "+00:00")
            )
            if created_at >= cutoff:
                date_str = created_at.strftime("%Y-%m-%d")
                frequency[date_str] += 1
        
        return dict(frequency)
    
    def get_language_distribution(
        self,
        user_id: str
    ) -> Dict[str, int]:
        """
        Get distribution of languages used in entries.
        
        Returns:
            Dict mapping language codes to counts
        """
        entries = self._get_all_user_entries(user_id)
        return dict(Counter(e.get("language_code", "unknown") for e in entries))
    
    def get_mood_distribution(
        self,
        user_id: str
    ) -> Dict[str, int]:
        """
        Get distribution of moods across entries.
        
        Returns:
            Dict mapping mood names to counts
        """
        entries = self._get_all_user_entries(user_id)
        moods = [e.get("mood") for e in entries if e.get("mood")]
        return dict(Counter(moods))
    
    def get_tag_frequency(
        self,
        user_id: str,
        top_n: int = 10
    ) -> List[tuple]:
        """
        Get most frequently used tags.
        
        Returns:
            List of (tag, count) tuples, sorted by frequency
        """
        entries = self._get_all_user_entries(user_id)
        tags = []
        for entry in entries:
            tags.extend(entry.get("tags", []))
        return Counter(tags).most_common(top_n)
    
    def get_activity_summary(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get activity summary for the last N days.
        
        Returns:
            Dict with summary statistics
        """
        entries = self._get_all_user_entries(user_id)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        recent_entries = [
            e for e in entries
            if datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) >= cutoff
        ]
        
        # Calculate stats
        total_entries = len(recent_entries)
        languages = Counter(e.get("language_code", "unknown") for e in recent_entries)
        moods = Counter(e.get("mood") for e in recent_entries if e.get("mood"))
        
        # Word count approximation
        total_words = sum(
            len(e.get("transcript", "").split()) for e in recent_entries
        )
        
        # Days with entries
        entry_dates = set(
            datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            for e in recent_entries
        )
        
        return {
            "period_days": days,
            "total_entries": total_entries,
            "total_words": total_words,
            "avg_words_per_entry": total_words // total_entries if total_entries else 0,
            "active_days": len(entry_dates),
            "top_language": languages.most_common(1)[0] if languages else None,
            "top_mood": moods.most_common(1)[0] if moods else None,
            "language_breakdown": dict(languages),
            "mood_breakdown": dict(moods)
        }
    
    def get_streak(self, user_id: str) -> int:
        """
        Calculate current journaling streak (consecutive days).
        
        Returns:
            Number of consecutive days with entries
        """
        entries = self._get_all_user_entries(user_id)
        if not entries:
            return 0
        
        # Get all unique dates
        dates = sorted(set(
            datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")).date()
            for e in entries
        ), reverse=True)
        
        if not dates:
            return 0
        
        # Check if there's an entry today or yesterday
        today = datetime.now(timezone.utc).date()
        if dates[0] < today - timedelta(days=1):
            return 0
        
        # Count consecutive days
        streak = 1
        for i in range(1, len(dates)):
            if dates[i-1] - dates[i] == timedelta(days=1):
                streak += 1
            else:
                break
        
        return streak
    
    def generate_insights(self, user_id: str) -> List[str]:
        """Generate text insights about journaling patterns."""
        insights = []
        summary = self.get_activity_summary(user_id, days=30)
        streak = self.get_streak(user_id)
        
        if streak > 0:
            insights.append(f"🔥 You're on a {streak}-day journaling streak!")
        
        if summary["total_entries"] > 0:
            insights.append(
                f"📊 You've made {summary['total_entries']} entries "
                f"in the last 30 days ({summary['total_words']} words total)."
            )
        
        if summary["top_language"]:
            lang, count = summary["top_language"]
            insights.append(f"🌐 Your most used language: {lang} ({count} entries)")
        
        if summary["top_mood"]:
            mood, count = summary["top_mood"]
            insights.append(f"😊 Most common mood: {mood} ({count} times)")
        
        return insights

