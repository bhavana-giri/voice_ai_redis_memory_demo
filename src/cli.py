"""Interactive CLI interface for Voice Journal."""
import asyncio
import uuid
from datetime import datetime
from typing import Optional

from .voice_journal import VoiceJournal
from .audio_storage import AudioStorage


class JournalCLI:
    """Interactive command-line interface for voice journaling."""
    
    COMMANDS = {
        "new": "Record a new journal entry",
        "history": "View conversation history",
        "entries": "List all entries for today",
        "timeline": "View recent entries timeline",
        "session": "Start a new session",
        "speak": "Have the journal speak a message",
        "tts": "Toggle text-to-speech on/off",
        "help": "Show available commands",
        "quit": "Exit the journal"
    }
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        tts_enabled: bool = True
    ):
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.journal = VoiceJournal(
            user_id=self.user_id,
            tts_enabled=tts_enabled
        )
        self.audio_storage = AudioStorage()
        self.running = False
    
    def print_banner(self):
        """Print welcome banner."""
        print("\n" + "="*60)
        print("🎙️  VOICE JOURNAL with Redis Agent Memory")
        print("="*60)
        print(f"👤 User: {self.user_id}")
        print(f"📝 Session: {self.journal.session_id}")
        print(f"🔊 TTS: {'Enabled' if self.journal.tts_enabled else 'Disabled'}")
        print("="*60)
        print("Type 'help' for commands or 'new' to record an entry")
        print("="*60 + "\n")
    
    def print_help(self):
        """Print available commands."""
        print("\n📖 Available Commands:")
        print("-" * 40)
        for cmd, desc in self.COMMANDS.items():
            print(f"  {cmd:12} - {desc}")
        print("-" * 40 + "\n")
    
    async def cmd_new(self, duration: int = 10):
        """Record a new journal entry."""
        print(f"\n📝 Recording new entry ({duration} seconds)...")
        
        entry = await self.journal.record_entry(duration=duration)
        
        # Store audio metadata
        entry_id = f"entry_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.audio_storage.store_audio_metadata(
            entry_id=entry_id,
            user_id=self.user_id,
            audio_file=entry["audio_file"],
            transcript=entry["transcript"],
            language_code=entry["language_code"],
            duration_seconds=duration
        )
        
        # Respond
        response = f"Got it! I've recorded your entry about: {entry['transcript'][:50]}..."
        await self.journal.respond(response, entry["language_code"])
        
        print(f"\n✅ Entry saved with ID: {entry_id}")
    
    async def cmd_history(self):
        """Show conversation history."""
        print("\n📜 Conversation History:")
        print("-" * 40)
        
        history = await self.journal.get_history()
        if not history:
            print("  No entries in current session.")
        else:
            for msg in history:
                role = "👤 You" if msg["role"] == "user" else "🤖 Journal"
                print(f"  {role}: {msg['content'][:100]}...")
        print("-" * 40 + "\n")
    
    async def cmd_entries(self):
        """List today's entries."""
        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n📅 Entries for {today}:")
        print("-" * 40)
        
        entries = self.audio_storage.get_entries_by_date(self.user_id, today)
        if not entries:
            print("  No entries today.")
        else:
            for e in entries:
                time_str = datetime.fromisoformat(
                    e["created_at"].replace("Z", "+00:00")
                ).strftime("%H:%M")
                print(f"  [{time_str}] ({e['language_code']}) {e['transcript'][:50]}...")
        print("-" * 40 + "\n")
    
    async def cmd_timeline(self, count: int = 10):
        """Show recent entries timeline."""
        print(f"\n📊 Recent Entries (last {count}):")
        print("-" * 40)
        
        entries = self.audio_storage.get_user_timeline(self.user_id, count=count)
        if not entries:
            print("  No entries yet.")
        else:
            for e in entries:
                dt = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
                print(f"  [{dt.strftime('%m/%d %H:%M')}] {e['transcript'][:40]}...")
        print("-" * 40 + "\n")
    
    async def cmd_session(self):
        """Start a new session."""
        new_session = await self.journal.new_session()
        print(f"\n🆕 New session started: {new_session}\n")
    
    async def cmd_speak(self, text: str):
        """Have the journal speak a message."""
        self.journal.speak(text)
    
    def cmd_tts(self):
        """Toggle TTS on/off."""
        self.journal.tts_enabled = not self.journal.tts_enabled
        status = "enabled" if self.journal.tts_enabled else "disabled"
        print(f"\n🔊 Text-to-speech {status}\n")
    
    async def process_command(self, cmd: str) -> bool:
        """Process a command. Returns False to quit."""
        parts = cmd.strip().lower().split()
        if not parts:
            return True
        
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        if command == "quit" or command == "exit":
            return False
        elif command == "help":
            self.print_help()
        elif command == "new":
            duration = int(args[0]) if args else 10
            await self.cmd_new(duration)
        elif command == "history":
            await self.cmd_history()
        elif command == "entries":
            await self.cmd_entries()
        elif command == "timeline":
            count = int(args[0]) if args else 10
            await self.cmd_timeline(count)
        elif command == "session":
            await self.cmd_session()
        elif command == "speak":
            text = " ".join(args) if args else "Hello from your voice journal!"
            await self.cmd_speak(text)
        elif command == "tts":
            self.cmd_tts()
        else:
            print(f"❓ Unknown command: {command}. Type 'help' for commands.")

        return True

    async def run(self):
        """Run the interactive CLI."""
        self.running = True
        self.print_banner()

        # Health check
        health = await self.journal.health_check()
        if not health["memory_server"]:
            print("⚠️  Warning: Memory server not available. Some features may not work.")

        # Welcome message
        self.journal.speak("Welcome to your voice journal. Say 'new' to record an entry.")

        while self.running:
            try:
                cmd = input("\n🎙️ journal> ").strip()
                if not await self.process_command(cmd):
                    break
            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

        # Cleanup
        print("\n👋 Goodbye! Closing journal...")
        await self.journal.close()


async def main():
    """Main entry point."""
    cli = JournalCLI(tts_enabled=True)
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())

