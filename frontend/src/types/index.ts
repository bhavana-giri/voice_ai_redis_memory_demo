export interface JournalEntry {
  id: string;
  transcript: string;
  language_code: string;
  created_at: string;
  duration_seconds: number;
  mood?: string;
  tags?: string[];
  audio_file?: string;
}

export interface RecordingState {
  isRecording: boolean;
  duration: number;
  audioLevel: number;
}

export interface PlaybackState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  entryId: string | null;
}

