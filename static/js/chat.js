// College Connect AI — Chat JS

document.addEventListener('DOMContentLoaded', () => {
  const textarea   = document.getElementById('chat-input');
  const sendBtn    = document.getElementById('chat-send');
  const msgArea    = document.getElementById('chat-messages');
  const typing     = document.getElementById('typing-indicator');
  const clearBtn   = document.getElementById('chat-clear');
  const chips      = document.querySelectorAll('.quick-chip');

  if (!textarea || !sendBtn || !msgArea) return;

  function timestamp() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Render Markdown-like formatting
  function renderMd(text) {
    if (!text) return '';
    let t = esc(text);
    t = t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    t = t.replace(/\*(.*?)\*/g,   '<em>$1</em>');
    t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:underline;">$1</a>');
    // paragraphs
    const parts = t.split('\n\n');
    return parts.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
  }

  function scrollBottom() {
    msgArea.scrollTop = msgArea.scrollHeight;
  }

  function appendUser(text) {
    const row = document.createElement('div');
    row.className = 'msg-row user-row';
    row.innerHTML = `
      <div class="bubble">${esc(text).replace(/\n/g,'<br>')}</div>
      <div class="msg-meta">${timestamp()}</div>`;
    msgArea.appendChild(row);
    scrollBottom();
  }

  function appendBot(data) {
    const row = document.createElement('div');
    row.className = 'msg-row bot-row';

    let srcHtml = data.source
      ? `<span class="src-badge">${esc(data.source)}</span>` : '';

    let sugHtml = '';
    if (data.quick_actions && data.quick_actions.length) {
      sugHtml = `<div class="bot-suggests">${
        data.quick_actions.map(a =>
          `<button class="sug-btn" data-q="${esc(a)}">${esc(a)}</button>`
        ).join('')
      }</div>`;
    }

    row.innerHTML = `
      <div class="bubble">
        ${renderMd(data.reply)}
        ${sugHtml}
      </div>
      <div class="msg-meta">${timestamp()} ${srcHtml}</div>`;

    // attach suggestion button listeners
    row.querySelectorAll('.sug-btn').forEach(b =>
      b.addEventListener('click', () => sendMsg(b.dataset.q))
    );

    msgArea.appendChild(row);
    scrollBottom();
  }

  async function sendMsg(overrideText) {
    const text = overrideText !== undefined
      ? overrideText.trim()
      : textarea.value.trim();
    if (!text) return;

    if (overrideText === undefined) {
      textarea.value = '';
      textarea.style.height = 'auto';
    }

    appendUser(text);
    showTyping();
    sendBtn.disabled = true;

    try {
      const res  = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      hideTyping();
      sendBtn.disabled = false;
      appendBot(data);
    } catch {
      hideTyping();
      sendBtn.disabled = false;
      appendBot({
        reply: 'Unable to connect. Please check your connection or visit the college office.',
        source: 'Connection Error'
      });
    }
  }

  function showTyping() {
    if (typing) { typing.style.display = 'flex'; scrollBottom(); }
  }
  function hideTyping() {
    if (typing) typing.style.display = 'none';
  }

  // Event listeners
  sendBtn.addEventListener('click', () => sendMsg());

  textarea.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMsg();
    }
  });

  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  });

  chips.forEach(c => c.addEventListener('click', () =>
    sendMsg(c.dataset.query || c.textContent.trim())
  ));

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      msgArea.innerHTML = `
        <div class="msg-row bot-row">
          <div class="bubble"><p>Chat cleared. Hi! How can I help you with Vande Mataram Degree College today?</p></div>
          <div class="msg-meta">${timestamp()}</div>
        </div>`;
    });
  }
});

function esc(s) {
  if (!s) return '';
  return String(s).replace(/[&<>'"]/g, c =>
    ({ '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;' }[c])
  );
}
