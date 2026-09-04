import { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, AlertTriangle } from "lucide-react";
import { chatApi } from "../services/api";

// FastAPI sends `detail` as a string for HTTPException, but as an array of
// objects for 422 validation errors — which must not reach the user as-is.
const readDetail = (err, fallback) => {
  const detail = err?.response?.data?.detail;
  return typeof detail === "string" ? detail : fallback;
};

export default function ReviewChat({ reviewId }) {
  const [sessionId, setSessionId] = useState(null); // null = no session yet
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [remaining, setRemaining] = useState(null);
  const [starting, setStarting] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  //bottomRef is used to scroll the chat to the bottom when new messages are added.
  const bottomRef = useRef(null);

  const outOfQuota = remaining === 0;

  // Keep the newest turn in view, including while the reply is pending.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const startSession = async () => {
    setStarting(true);
    setError(null);
    try {
      const { data } = await chatApi.startSession(reviewId);
      setSessionId(data._id);
      setRemaining(data.remainingMessagesToday);

      // start reuses an existing session for this review rather than creating a
      // second one, so a returning user has a transcript waiting to be restored.
      const { data: history } = await chatApi.getMessages(data._id);
      setMessages(history);
    } catch (err) {
      setError(readDetail(err, "Couldn't open the chat. Please try again."));
    } finally {
      setStarting(false);
    }
  };

  const sendMessage = async () => {
    const text = draft.trim();
    if (!text || sending || outOfQuota) return;

    setDraft("");
    setError(null);
    setSending(true);
    // Echoed straight away: the model call takes several seconds, and a message
    // that vanishes on submit reads as a broken send.
    setMessages((prev) => [...prev, { _id: "pending", role: "user", content: text }]);

    try {
      const { data } = await chatApi.sendMessage(sessionId, text);
      // Swap the local echo for the two persisted turns.
      setMessages((prev) => [...prev.slice(0, -1), data.userMessage, data.reply]);
      setRemaining(data.remainingMessagesToday);
    } catch (err) {
      setMessages((prev) => prev.slice(0, -1)); // nothing was saved server-side
      setDraft(text); // hand back what they typed instead of losing it

      const status = err.response?.status;
      if (status === 429) {
        // The cap is per user per UTC day, so another tab or an earlier session
        // can exhaust it while this one still believes it has budget.
        setRemaining(0);
        setError(
          `${readDetail(err, "Daily chat limit reached")} — your quota resets at midnight UTC.`,
        );
      } else if (status === 502) {
        setError("The AI service didn't respond. Please try again in a moment.");
      } else {
        setError(readDetail(err, "Couldn't send your message. Please try again."));
      }
    } finally {
      setSending(false);
    }
  };

  // ── State 1: no session yet ────────────────────────────────────────────
  if (!sessionId) {
    return (
      <div className="card review-chat-start">
        <div className="review-chat-start-copy">
          <MessageSquare size={18} color="var(--accent)" />
          <div>
            <p className="review-chat-start-title">Chat about this review</p>
            <p className="review-chat-start-sub">
              Ask follow-up questions about the findings or the code.
            </p>
          </div>
        </div>
        {error && (
          <p className="review-chat-error">
            <AlertTriangle size={14} /> {error}
          </p>
        )}
        <button className="btn btn-primary" onClick={startSession} disabled={starting}>
          {starting ? "Opening…" : "Chat about this review"}
        </button>
      </div>
    );
  }

  // ── State 2: session active ────────────────────────────────────────────
  return (
    <div className="card review-chat">
      <div className="review-chat-header">
        <div className="review-section-title-wrap">
          <MessageSquare size={18} color="var(--accent)" />
          <span className="review-section-title">CHAT</span>
        </div>
        {remaining !== null && (
          <span className={`review-chat-quota${remaining <= 3 ? " review-chat-quota-low" : ""}`}>
            {remaining} {remaining === 1 ? "message" : "messages"} left today
          </span>
        )}
      </div>

      <div className="review-chat-messages">
        {messages.length === 0 && !sending && (
          <p className="review-chat-empty">No messages yet — ask the first question.</p>
        )}

        {messages.map((msg, i) => (
          <div
            key={msg._id === "pending" ? `pending-${i}` : msg._id}
            className={`review-chat-msg review-chat-msg-${msg.role}`}
          >
            <span className="review-chat-msg-role">{msg.role === "user" ? "You" : "CodeLens"}</span>
            <p className="review-chat-msg-text">{msg.content}</p>
          </div>
        ))}

        {sending && (
          <div className="review-chat-msg review-chat-msg-model">
            <span className="review-chat-msg-role">CodeLens</span>
            <p className="review-chat-msg-text review-chat-typing">
              <span /><span /><span />
            </p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className={`review-chat-error${outOfQuota ? " review-chat-error-quota" : ""}`}>
          <AlertTriangle size={14} /> {error}
        </p>
      )}

      <div className="review-chat-input">
        <input
          rows={1}
          className="review-chat-input-field"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown = {(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          placeholder={
            outOfQuota ? "Daily limit reached — back tomorrow" : "Ask about this review…"
          }
          disabled={sending || outOfQuota}
        />  
        <button
          className="btn btn-primary"
          onClick={sendMessage}
          disabled={sending || outOfQuota || !draft.trim()}
        >
          <Send size={15} />
          {sending ? "Sending…" : "Send"}
        </button>
      </div>
    </div>
  );
}
