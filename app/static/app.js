// Virtual Engineer - frontend chat logic
const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const suggestionsBar = document.getElementById("suggestions");
const attachBtn = document.getElementById("attach");
const fileInput = document.getElementById("file-input");
const attachments = document.getElementById("attachments");

// Conversation history sent to the backend for context.
const history = [];
// Files staged for analysis (until the user hits Send).
let selectedFiles = [];

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

// --- File attachment + document analysis -----------------------------------
attachBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  for (const f of fileInput.files) selectedFiles.push(f);
  fileInput.value = ""; // allow re-selecting the same file
  renderAttachments();
});

function renderAttachments() {
  attachments.innerHTML = "";
  selectedFiles.forEach((f, i) => {
    const chip = document.createElement("span");
    chip.className = "attachment";
    chip.innerHTML = `📄 ${escapeHtml(f.name)} <button title="Remove" data-i="${i}">×</button>`;
    chip.querySelector("button").onclick = () => {
      selectedFiles.splice(i, 1);
      renderAttachments();
    };
    attachments.appendChild(chip);
  });
  attachBtn.classList.toggle("has-files", selectedFiles.length > 0);
}

function fmtNum(n) {
  return (n || 0).toLocaleString();
}

// Deloitte brand chart sequence (green first) — distinct color per category.
const BAR_PALETTE = ["#86BC25", "#00A3E0", "#282728", "#63C631", "#A0DCFF", "#005587", "#B7E320", "#0076A8"];

function barRows(obj, max) {
  const entries = Object.entries(obj || {});
  if (!entries.length) return "<p class='muted'>None detected.</p>";
  const top = Math.max(1, ...entries.map(([, v]) => v));
  return entries
    .map(
      ([k, v], i) => `
      <div class="bar-row">
        <span class="bar-label">${escapeHtml(k)}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${(v / top) * 100}%;background:${BAR_PALETTE[i % BAR_PALETTE.length]}"></span></span>
        <span class="bar-val">${v}</span>
      </div>`
    )
    .join("");
}

function trendChart(trends) {
  if (!trends || !trends.length) return "";
  const max = Math.max(1, ...trends.map((t) => t.issues + t.requests));
  const bars = trends
    .map(
      (t) => `
      <div class="trend-col" title="${t.period}: ${t.issues} issues, ${t.requests} requests">
        <span class="trend-bar issues" style="height:${(t.issues / max) * 100}%"></span>
        <span class="trend-bar requests" style="height:${(t.requests / max) * 100}%"></span>
        <span class="trend-label">${t.period.slice(2)}</span>
      </div>`
    )
    .join("");
  return `
    <h4>📈 Trend over time</h4>
    <div class="trend-legend"><span class="dot issues"></span>Issues <span class="dot requests"></span>Requests</div>
    <div class="trend-chart">${bars}</div>`;
}

function renderReport(data) {
  const issues = data.issues || [];
  const requests = data.requests || [];
  const files = data.file_summaries || [];

  const fileRows = files
    .map(
      (f) => `<tr><td>${escapeHtml(f.filename)}</td><td>${f.filetype}</td>
              <td>${fmtNum(f.words)}</td><td>${f.error ? "⚠️ " + escapeHtml(f.error) : "ok"}</td></tr>`
    )
    .join("");

  const terms = (data.top_terms || [])
    .map(([w, c]) => `<span class="term">${escapeHtml(w)} <em>${c}</em></span>`)
    .join("");

  const examples = (list) =>
    list
      .slice(0, 4)
      .map(
        (f) =>
          `<li><span class="cat">${escapeHtml(f.category)}</span> ${escapeHtml(f.snippet)}
           <span class="src">— ${escapeHtml(f.source)}${f.period ? ", " + f.period : ""}</span></li>`
      )
      .join("");

  const notes = (data.notes || []).map((n) => `<p class="note">${escapeHtml(n)}</p>`).join("");

  return `
  <div class="report">
    <span class="intent-tag">document analysis</span>
    ${renderMarkdown(data.summary || "")}

    <div class="stat-cards">
      <div class="stat"><b>${fmtNum(data.total_files)}</b><span>files</span></div>
      <div class="stat"><b>${fmtNum(data.total_words)}</b><span>words</span></div>
      <div class="stat"><b>${fmtNum(issues.length)}</b><span>issues</span></div>
      <div class="stat"><b>${fmtNum(requests.length)}</b><span>requests</span></div>
    </div>

    <h4>🐞 Issue themes</h4>
    ${barRows(data.issue_categories)}
    ${issues.length ? `<ul class="examples">${examples(issues)}</ul>` : ""}

    <h4>💡 Request themes</h4>
    ${barRows(data.request_categories)}
    ${requests.length ? `<ul class="examples">${examples(requests)}</ul>` : ""}

    ${trendChart(data.trends)}

    ${terms ? `<h4>🔑 Top themes</h4><div class="terms">${terms}</div>` : ""}

    <h4>📂 Files read</h4>
    <table class="file-table"><thead><tr><th>File</th><th>Type</th><th>Words</th><th>Status</th></tr></thead>
    <tbody>${fileRows}</tbody></table>

    ${notes}
  </div>`;
}

async function runAnalysis(files) {
  const names = files.map((f) => f.name).join(", ");
  addMessage("user", `📎 Analyze: ${names}`);
  const typing = addMessage("assistant", "_Reading and analyzing your documents…_");
  typing.parentElement.classList.add("typing");
  sendBtn.disabled = true;

  try {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    const data = await res.json();
    typing.parentElement.remove();
    if (!data.ok) {
      addMessage("assistant", "⚠️ " + (data.error || "Could not analyze those files."));
    } else {
      const bubble = addMessage("assistant", "");
      bubble.innerHTML = renderReport(data);
      bubble.classList.add("wide");
      chat.scrollTop = chat.scrollHeight;
    }
  } catch (err) {
    typing.parentElement.classList.remove("typing");
    typing.innerHTML = renderMarkdown("⚠️ Analysis failed. Is the server running?");
  } finally {
    sendBtn.disabled = false;
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  // If files are staged, analyze them (this takes priority).
  if (selectedFiles.length > 0) {
    const files = selectedFiles;
    selectedFiles = [];
    renderAttachments();
    runAnalysis(files);
    return;
  }
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
