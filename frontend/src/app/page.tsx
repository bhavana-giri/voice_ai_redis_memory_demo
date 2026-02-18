'use client';

import { useState } from 'react';
import Sidebar from '@/components/Sidebar';
import SearchBar from '@/components/SearchBar';
import EntryCard from '@/components/EntryCard';
import StatsCard from '@/components/StatsCard';
import RecordingModal from '@/components/RecordingModal';
import ChatInterface from '@/components/ChatInterface';
import { JournalEntry, PlaybackState } from '@/types';

// Mock data for demonstration
const mockEntries: JournalEntry[] = [
  {
    id: '1',
    transcript: 'Today was a productive day. I managed to complete the voice journal project and learned a lot about Redis Agent Memory Server.',
    language_code: 'en-IN',
    created_at: new Date().toISOString(),
    duration_seconds: 45,
    mood: 'happy',
    tags: ['work', 'coding'],
  },
  {
    id: '2',
    transcript: 'Had a great meeting with the team today. We discussed the roadmap for Q1 and everyone seemed excited.',
    language_code: 'en-IN',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    duration_seconds: 32,
    mood: 'excited',
    tags: ['work', 'meeting'],
  },
  {
    id: '3',
    transcript: 'आज मैंने हिंदी में अपनी पहली जर्नल एंट्री रिकॉर्ड की। यह बहुत अच्छा अनुभव था।',
    language_code: 'hi-IN',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    duration_seconds: 28,
    mood: 'grateful',
    tags: ['personal', 'hindi'],
  },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [entries, setEntries] = useState<JournalEntry[]>(mockEntries);
  const [isRecordingModalOpen, setIsRecordingModalOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [playback, setPlayback] = useState<PlaybackState>({
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    entryId: null,
  });

  const filteredEntries = entries.filter((entry) =>
    entry.transcript.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handlePlay = (entryId: string) => {
    const entry = entries.find((e) => e.id === entryId);
    if (entry) {
      setPlayback({ isPlaying: true, currentTime: 0, duration: entry.duration_seconds, entryId });
    }
  };

  const handlePause = () => setPlayback((prev) => ({ ...prev, isPlaying: false }));

  const handleDelete = (entryId: string) => {
    setEntries((prev) => prev.filter((e) => e.id !== entryId));
  };

  const handleFavorite = (entryId: string) => console.log('Favorite:', entryId);

  const handleSaveRecording = (
    audioBlob: Blob,
    duration: number,
    transcript?: string,
    sessionId?: string,
    languageCode?: string
  ) => {
    const newEntry: JournalEntry = {
      id: sessionId || Date.now().toString(),
      transcript: transcript || 'New voice entry',
      language_code: languageCode || 'en-IN',
      created_at: new Date().toISOString(),
      duration_seconds: duration,
    };
    setEntries((prev) => [newEntry, ...prev]);
    setIsRecordingModalOpen(false);
    console.log('[OK] Entry saved with session:', sessionId);
  };

  return (
    <div className="flex h-screen gradient-bg">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="p-6 border-b border-gray-200/50">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Voice Journal</h1>
              <p className="text-sm text-gray-500">Capture your thoughts with your voice</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setIsChatOpen(true)}
                className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl text-white font-medium hover:from-emerald-400 hover:to-teal-500 transition-all shadow-lg shadow-teal-500/25"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Chat with Journal
              </button>
              <button
                onClick={() => setIsRecordingModalOpen(true)}
                className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-violet-500 to-purple-600 rounded-xl text-white font-medium hover:from-violet-400 hover:to-purple-500 transition-all shadow-lg shadow-purple-500/25"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                </svg>
                New Recording
              </button>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mb-6">
            <StatsCard title="Total Entries" value={entries.length} icon="📝" change="+3" changeType="positive" colorClass="bg-purple-100" />
            <StatsCard title="This Week" value="12" icon="📅" change="+5" changeType="positive" colorClass="bg-yellow-100" />
            <StatsCard title="Total Duration" value="2h 15m" icon="⏱️" colorClass="bg-orange-100" />
            <StatsCard title="Streak" value="7 days" icon="🔥" change="Best!" changeType="positive" colorClass="bg-green-100" />
          </div>

          <SearchBar value={searchQuery} onChange={setSearchQuery} />
        </header>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-3">
            {filteredEntries.length > 0 ? (
              filteredEntries.map((entry, index) => (
                <EntryCard key={entry.id} entry={entry} playback={playback} onPlay={handlePlay} onPause={handlePause} onDelete={handleDelete} onFavorite={handleFavorite} colorIndex={index} />
              ))
            ) : (
              <div className="text-center py-12">
                <p className="text-gray-500 mb-4">No entries found</p>
                <button onClick={() => setIsRecordingModalOpen(true)} className="text-purple-600 hover:text-purple-500">
                  Create your first entry
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      <RecordingModal isOpen={isRecordingModalOpen} onClose={() => setIsRecordingModalOpen(false)} onSave={handleSaveRecording} />
      <ChatInterface isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
}
