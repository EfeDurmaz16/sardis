"use client";
export default function ChatInterface({ agentId: _a, agentName: _n, onClose }: { agentId: string; agentName: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="card max-w-md w-full mx-4 p-6 text-center">
        <p className="text-white mb-4">Chat interface coming soon</p>
        <button onClick={onClose} className="px-4 py-2 bg-sardis-500 text-dark-400 font-medium rounded-lg hover:bg-sardis-400 transition-colors">Close</button>
      </div>
    </div>
  )
}
