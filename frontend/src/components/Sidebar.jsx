function Sidebar({
  activeConversationId,
  conversations,
  onNewConversation,
  onSelectConversation,
}) {
  return (
    <div className="flex h-full min-h-[320px] flex-col border-l border-slate-200/80 bg-[linear-gradient(180deg,_rgba(255,255,255,0.55),_rgba(245,244,251,0.86))] px-4 py-6 text-slate-700 lg:min-h-[calc(100vh-7.5rem)] lg:px-6">
      <div className="pb-5">
        <button
          type="button"
          onClick={onNewConversation}
          className="w-full rounded-2xl bg-blue-500 px-4 py-3 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(96,126,203,0.25)] transition hover:bg-blue-600"
        >
          New Chat
        </button>
      </div>

      <div className="pb-5">
        <p className="text-3xl font-light tracking-tight text-slate-700">
          Past query
        </p>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto pr-1">
        {conversations.map((conversation) => {
          const isActive = conversation.id === activeConversationId
          return (
            <button
              key={conversation.id}
              type="button"
              onClick={() => onSelectConversation(conversation.id)}
              className={`w-full rounded-2xl bg-white px-5 py-4 text-left shadow-[0_12px_24px_rgba(159,167,194,0.18)] transition ${
                isActive
                  ? 'ring-2 ring-blue-200'
                  : 'hover:translate-y-[-1px]'
              }`}
            >
              <p className="line-clamp-2 text-sm font-medium text-slate-700">
                {conversation.title}
              </p>
              <p className="mt-2 text-xs text-slate-400">
                {conversation.lastQuery ?? 'Welcome conversation'}
              </p>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default Sidebar
