function ChatBubble({ role, children }) {
  const isUser = role === 'user'

  return (
    <div className={`flex min-w-0 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={
          isUser
            ? 'min-w-0 max-w-[min(42rem,92%)] overflow-hidden rounded-2xl rounded-br-md bg-slate-950 px-5 py-4 text-white shadow-[0_18px_40px_rgba(15,23,42,0.18)] [overflow-wrap:anywhere]'
            : 'min-w-0 max-w-[min(56rem,92%)] overflow-hidden rounded-2xl rounded-bl-md border border-slate-200/80 bg-white px-5 py-4 shadow-[0_12px_30px_rgba(15,23,42,0.06)] [overflow-wrap:anywhere]'
        }
      >
        {children}
      </div>
    </div>
  )
}

export default ChatBubble
