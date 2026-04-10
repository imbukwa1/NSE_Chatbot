function MicIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 1 1-14 0v-2" />
      <path d="M12 19v3" />
    </svg>
  )
}

function SendIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      className="h-5 w-5"
      aria-hidden="true"
    >
      <path d="m6.5 12 3.2 3.2L17.5 7.5" />
    </svg>
  )
}

function InputBar({
  isListening,
  isLoading,
  onMicClick,
  onQueryChange,
  onSubmit,
  query,
  voiceSupported,
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-3">
      <div className="flex items-center gap-3 rounded-[1.75rem] border border-slate-300/80 bg-white px-4 py-3 shadow-[0_16px_40px_rgba(173,178,214,0.24)]">
        <button
          type="button"
          onClick={onMicClick}
          disabled={!voiceSupported || isLoading}
          className={`inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full transition ${
            isListening
              ? 'bg-rose-50 text-rose-600'
              : 'bg-transparent text-slate-500'
          } disabled:cursor-not-allowed disabled:opacity-50`}
          title={voiceSupported ? 'Use voice input' : 'Voice input is not supported'}
        >
          <MicIcon />
        </button>

        <input
          type="text"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Ask query"
          className="h-12 flex-1 bg-transparent px-1 text-2xl font-light text-slate-700 outline-none placeholder:text-slate-400 sm:text-[2rem]"
        />

        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="inline-flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white shadow-[0_12px_24px_rgba(96,126,203,0.3)] transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <SendIcon />
        </button>
      </div>

      <div className="flex min-h-5 items-center justify-between px-1 text-xs text-slate-400">
        <span>
          {isListening
            ? 'Listening... speak naturally and pause when finished.'
            : 'Use voice or type a query to explore NSE data and analysis.'}
        </span>
        {!voiceSupported && <span>Voice input unavailable in this browser.</span>}
      </div>
    </form>
  )
}

export default InputBar
