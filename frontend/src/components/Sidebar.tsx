'use client';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export default function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  const tabs = [
    { id: 'all', label: 'All Notes', icon: '📝', count: 24 },
    { id: 'recent', label: 'Recent', icon: '🕐', count: 8 },
    { id: 'favorites', label: 'Favorites', icon: '⭐', count: 5 },
    { id: 'trash', label: 'Trash', icon: '🗑️', count: 2 },
  ];

  const folders = [
    { id: 'personal', label: 'Personal', color: '#8b5cf6' },
    { id: 'work', label: 'Work', color: '#22c55e' },
    { id: 'ideas', label: 'Ideas', color: '#f59e0b' },
  ];

  return (
    <aside className="w-64 glass-card h-screen flex flex-col border-r border-white/20">
      {/* Logo */}
      <div className="p-6 border-b border-gray-200/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/25">
            <span className="text-xl">🎙️</span>
          </div>
          <div>
            <h1 className="font-bold text-lg text-gray-800">Voice Journal</h1>
            <p className="text-xs text-gray-500">Your thoughts, captured</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto">
        <div className="space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition-all ${
                activeTab === tab.id
                  ? 'bg-purple-500/20 text-purple-700 font-medium'
                  : 'text-gray-600 hover:bg-white/50 hover:text-gray-800'
              }`}
            >
              <div className="flex items-center gap-3">
                <span>{tab.icon}</span>
                <span className="text-sm">{tab.label}</span>
              </div>
              <span className="text-xs bg-white/60 text-gray-600 px-2 py-1 rounded-full">{tab.count}</span>
            </button>
          ))}
        </div>

        {/* Folders */}
        <div className="mt-8">
          <h3 className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Folders
          </h3>
          <div className="space-y-1">
            {folders.map((folder) => (
              <button
                key={folder.id}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-gray-600 hover:bg-white/50 hover:text-gray-800 transition-all"
              >
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: folder.color }}
                />
                <span className="text-sm">{folder.label}</span>
              </button>
            ))}
            <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-gray-400 hover:bg-white/50 hover:text-gray-600 transition-all">
              <span className="text-lg">+</span>
              <span className="text-sm">New Folder</span>
            </button>
          </div>
        </div>
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-gray-200/50">
        <div className="flex items-center gap-3 px-2">
          <div className="w-10 h-10 bg-gradient-to-br from-violet-400 to-purple-500 rounded-full flex items-center justify-center text-white font-bold shadow-lg shadow-purple-500/25">
            U
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-800">User</p>
            <p className="text-xs text-gray-500">Free Plan</p>
          </div>
          <button className="text-gray-400 hover:text-gray-600">⚙️</button>
        </div>
      </div>
    </aside>
  );
}

