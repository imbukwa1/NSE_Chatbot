function Sidebar({
  activeConversationId,
  conversations,
  onNewConversation,
  onSelectConversation,
}) {
  return (
    <div className="flex h-full min-h-[320px] flex-col border-l border-slate-200/80 bg-white/65 px-4 py-5 text-slate-700 lg:min-h-[calc(100vh-4.75rem)] lg:px-5">
      <div className="pb-4">
        <button
          type="button"
          onClick={onNewConversation}
          className="w-full rounded-2xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(37,99,235,0.2)] transition hover:bg-blue-700"
        >
          New Chat
        </button>
      </div>

      <div className="pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
          Past conversations
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        {conversations.map((conversation) => {
          const isActive = conversation.id === activeConversationId
          const preview = conversation.lastQuery ?? 'Welcome to NSE AI Advisor'

          return (
            <button
              key={conversation.id}
              type="button"
              onClick={() => onSelectConversation(conversation.id)}
              className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                isActive
                  ? 'border-blue-200 bg-blue-50/70 shadow-[0_12px_28px_rgba(37,99,235,0.1)]'
                  : 'border-slate-200 bg-white shadow-sm hover:border-blue-100'
              }`}
            >
              <p className="line-clamp-1 text-sm font-semibold text-slate-800">
                {conversation.title}
              </p>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-400">
                {preview}
              </p>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default Sidebar
