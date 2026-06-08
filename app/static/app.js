// Virtual Engineer - frontend chat logic
const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const suggestionsBar = document.getElementById("suggestions");

// Conversation history sent to the backend for context.
const history = [];

// --- Tiny, safe markdown renderer (bold, inline code, code fences) ---------
function escapeHtml(s) {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderMarkdown(text) {
  const parts = text.split(/```/);
  let html = "";
  parts.forEach((part, i) => {
    if (i % 2 === 1) {
      // inside a code fence; drop an optional language tag on the first line
      const body = part.replace(/^[a-zA-Z]*\n/, "");
      html += `<pre><code>${escapeHtml(body)}</code></pre>`;
    } else {
      let p = escapeHtml(part)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/`(.+?)`/g, "<code>$1</code>");
      p = p
        .split(/\n{2,}/)
        .map((para) => `<p>${para.replaceAll("\n", "<br/>")}</p>`)
        .join("");
      html += p;
    }
  });
  return html;
}

function addMessage(role, text, intent) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  let inner = "";
  if (role === "assistant" && intent) {
    inner += `<span class="intent-tag">${intent}</span>`;
  }
  inner += renderMarkdown(text);
  bubble.innerHTML = inner;
  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

function renderSuggestions(items) {
  suggestionsBar.innerHTML = "";
  (items || []).forEach((s) => {
    const chip = document.createElement("button");
    chip.className = "suggestion";
    chip.type = "button";
    chip.textContent = s;
    chip.onclick = () => {
      input.value = s;
      input.focus();
    };
    suggestionsBar.appendChild(chip);
  });
}

async function send(message) {
  addMessage("user", message);
  history.push({ role: "user", content: message });
  suggestionsBar.innerHTML = "";

  const typing = addMessage("assistant", "_thinking…_");
  typing.parentElement.classList.add("typing");
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: history.slice(0, -1) }),
    });
    const data = await res.json();
    typing.parentElement.remove();
    addMessage("assistant", data.reply, data.intent);
    history.push({ role: "assistant", content: data.reply });
    renderSuggestions(data.suggestions);
  } catch (err) {
    typing.parentElement.classList.remove("typing");
    typing.innerHTML = renderMarkdown("⚠️ Couldn't reach the server. Is it running?");
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  input.style.height = "auto";
  send(message);
});

// Enter sends, Shift+Enter makes a newline.
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// Auto-grow the textarea.
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});

input.focus();
