'use client';

import { useState, useEffect } from 'react';
import { JournalEntry, PlaybackState } from '@/types';

interface EntryCardProps {
  entry: JournalEntry;
  playback: PlaybackState;
  onPlay: (entryId: string) => void;
  onPause: () => void;
  onDelete: (entryId: string) => void;
  onFavorite: (entryId: string) => void;
  colorIndex?: number;
}

const cardColors = [
  'bg-purple-100/80',
  'bg-yellow-100/80',
  'bg-orange-100/80',
  'bg-green-100/80',
];

export default function EntryCard({
  entry,
  playback,
  onPlay,
  onPause,
  onDelete,
  onFavorite,
  colorIndex = 0,
}: EntryCardProps) {
  const [formattedDate, setFormattedDate] = useState<string>('');
  const isPlaying = playback.isPlaying && playback.entryId === entry.id;
  const cardColor = cardColors[colorIndex % cardColors.length];

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format date on client side only to avoid hydration mismatch
  useEffect(() => {
    const date = new Date(entry.created_at);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      setFormattedDate(date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }));
    } else if (days === 1) {
      setFormattedDate('Yesterday');
    } else if (days < 7) {
      setFormattedDate(date.toLocaleDateString('en-US', { weekday: 'long' }));
    } else {
      setFormattedDate(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
    }
  }, [entry.created_at]);

  const moodEmoji: Record<string, string> = {
    happy: '😊',
    sad: '😢',
    excited: '🤩',
    calm: '😌',
    anxious: '😰',
    grateful: '🙏',
  };

  return (
    <div className={`${cardColor} rounded-2xl p-4 hover:shadow-md transition-all group border border-white/50`}>
      <div className="flex items-start gap-4">
        {/* Play/Pause Button */}
        <button
          onClick={() => (isPlaying ? onPause() : onPlay(entry.id))}
          className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-all shadow-sm ${
            isPlaying
              ? 'bg-purple-600 text-white'
              : 'bg-white/80 text-gray-600 hover:bg-purple-500 hover:text-white'
          }`}
        >
          {isPlaying ? (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-gray-500">{formattedDate || '...'}</span>
            <span className="text-xs text-gray-400">•</span>
            <span className="text-xs text-gray-500">{formatDuration(entry.duration_seconds)}</span>
            {entry.mood && (
              <>
                <span className="text-xs text-gray-400">•</span>
                <span>{moodEmoji[entry.mood] || '📝'}</span>
              </>
            )}
          </div>

          <p className="text-sm text-gray-700 line-clamp-2 mb-2">
            {entry.transcript}
          </p>

          {/* Tags */}
          {entry.tags && entry.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {entry.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-xs px-2 py-0.5 bg-white/60 text-gray-600 rounded-full"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}

          {/* Progress bar when playing */}
          {isPlaying && (
            <div className="mt-3">
              <div className="h-1 bg-white/50 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 transition-all"
                  style={{
                    width: `${(playback.currentTime / playback.duration) * 100}%`,
                  }}
                />
              </div>
              <div className="flex justify-between mt-1 text-xs text-gray-500">
                <span>{formatDuration(playback.currentTime)}</span>
                <span>{formatDuration(playback.duration)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onFavorite(entry.id)}
            className="p-2 text-gray-400 hover:text-yellow-500 transition-colors"
          >
            ⭐
          </button>
          <button
            onClick={() => onDelete(entry.id)}
            className="p-2 text-gray-400 hover:text-red-500 transition-colors"
          >
            🗑️
          </button>
        </div>
      </div>
    </div>
  );
}

