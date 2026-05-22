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
  placeholder = 'Ask about Safaricom, KCB, dividends, market trends...',
  query,
  voiceSupported,
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <div className="flex items-center gap-2.5 rounded-[1.35rem] border border-slate-200 bg-white px-3.5 py-2.5 shadow-[0_14px_34px_rgba(96,126,203,0.1)]">
        <button
          type="button"
          onClick={onMicClick}
          disabled={!voiceSupported || isLoading}
          className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition ${
            isListening
              ? 'bg-blue-50 text-blue-600'
              : 'bg-slate-50 text-slate-500 hover:bg-blue-50 hover:text-blue-600'
          } disabled:cursor-not-allowed disabled:opacity-50`}
          title={voiceSupported ? 'Use voice input' : 'Voice input is not supported'}
        >
          <MicIcon />
        </button>

        <input
          type="text"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={placeholder}
          className="h-10 flex-1 bg-transparent px-1 text-sm text-slate-700 outline-none placeholder:text-slate-400"
        />

        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white shadow-[0_10px_22px_rgba(37,99,235,0.2)] transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <SendIcon />
        </button>
      </div>

      <div className="flex min-h-4 items-center justify-between px-1 text-[11px] text-slate-400">
        <span>
          {isListening
            ? 'Listening... speak naturally and pause when finished.'
            : 'Voice and text are available for simple NSE research.'}
        </span>
        {!voiceSupported && <span>Voice input unavailable in this browser.</span>}
      </div>
    </form>
  )
}

export default InputBar
