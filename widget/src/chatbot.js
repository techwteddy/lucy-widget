(function() {
  'use strict';

  // Read config from script tag data attributes
  const script = document.currentScript || document.querySelector('script[data-chatbot-id]');
  const CHATBOT_ID = script.getAttribute('data-chatbot-id');
  const API_KEY = script.getAttribute('data-api-key') || '';
  const POSITION = script.getAttribute('data-position') || 'bottom-right';
  const PRIMARY_COLOR = script.getAttribute('data-primary-color') || '#3B82F6';
  const TITLE = script.getAttribute('data-title') || 'Chat with Lucy';

  // Auto-detect API host from script src
  const API_HOST = (() => {
    const src = script.src || '';
    try {
      const url = new URL(src);
      return url.origin;
    } catch {
      return 'http://localhost:8000';
    }
  })();

  const WS_HOST = API_HOST.replace(/^http/, 'ws');

  // Session persistence
  const SESSION_ID = (() => {
    const key = `chatbot_session_${CHATBOT_ID}`;
    let id = sessionStorage.getItem(key);
    if (!id) {
      id = 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
      sessionStorage.setItem(key, id);
    }
    return id;
  })();

  // State
  let ws = null;
  let reconnectDelay = 1000;
  let isOpen = false;
  let currentBotMessage = null;
  let currentBotText = '';
  let welcomeShown = false;
  let heartbeatInterval = null;

  // CSS styles (injected into Shadow DOM)
  const STYLES = `
    :host {
      all: initial;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    .bubble {
      position: fixed;
      ${POSITION === 'bottom-left' ? 'left: 24px;' : 'right: 24px;'}
      bottom: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: ${PRIMARY_COLOR};
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 4px 20px rgba(0,0,0,0.25);
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      z-index: 2147483647;
      border: none;
      outline: none;
    }

    .bubble:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(0,0,0,0.3); }
    .bubble:active { transform: scale(0.96); }

    .bubble svg { width: 28px; height: 28px; fill: white; }

    .window {
      position: fixed;
      ${POSITION === 'bottom-left' ? 'left: 24px;' : 'right: 24px;'}
      bottom: 96px;
      width: 360px;
      height: 520px;
      background: white;
      border-radius: 16px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.18);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 2147483646;
      transform: scale(0.95) translateY(10px);
      opacity: 0;
      pointer-events: none;
      transition: transform 0.25s cubic-bezier(0.34,1.56,0.64,1), opacity 0.2s ease;
    }

    .window.open {
      transform: scale(1) translateY(0);
      opacity: 1;
      pointer-events: all;
    }

    .header {
      background: ${PRIMARY_COLOR};
      color: white;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 64px;
    }

    .header-title { font-size: 16px; font-weight: 600; }
    .header-subtitle { font-size: 12px; opacity: 0.85; margin-top: 2px; }

    .close-btn {
      background: none;
      border: none;
      color: white;
      cursor: pointer;
      padding: 4px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      opacity: 0.8;
      transition: opacity 0.15s;
    }
    .close-btn:hover { opacity: 1; }
    .close-btn svg { width: 20px; height: 20px; fill: white; }

    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }

    .msg {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 14px;
      font-size: 14px;
      line-height: 1.5;
      word-break: break-word;
    }

    .msg.user {
      align-self: flex-end;
      background: ${PRIMARY_COLOR};
      color: white;
      border-bottom-right-radius: 4px;
    }

    .msg.bot {
      align-self: flex-start;
      background: #f1f5f9;
      color: #1e293b;
      border-bottom-left-radius: 4px;
    }

    .msg.bot strong { font-weight: 600; }
    .msg.bot em { font-style: italic; }
    .msg.bot code {
      background: #e2e8f0; padding: 1px 5px; border-radius: 4px;
      font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.9em;
    }
    .msg.bot a { color: ${PRIMARY_COLOR}; text-decoration: underline; }
    .msg.bot a:hover { opacity: 0.8; }
    .msg.bot ul { margin: 4px 0; padding-left: 18px; list-style: disc; }
    .msg.bot li { margin: 2px 0; }

    .typing-indicator {
      display: flex;
      gap: 4px;
      align-items: center;
      padding: 12px 14px;
    }

    .dot {
      width: 8px; height: 8px;
      background: #94a3b8;
      border-radius: 50%;
      animation: bounce 1.2s infinite;
    }
    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    .input-area {
      padding: 12px 16px;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 8px;
      align-items: flex-end;
    }

    .input {
      flex: 1;
      border: 1.5px solid #e2e8f0;
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 14px;
      resize: none;
      max-height: 120px;
      outline: none;
      font-family: inherit;
      color: #1e293b;
      transition: border-color 0.15s;
    }
    .input:focus { border-color: ${PRIMARY_COLOR}; }
    .input::placeholder { color: #94a3b8; }

    .send-btn {
      width: 40px; height: 40px;
      border-radius: 10px;
      background: ${PRIMARY_COLOR};
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: opacity 0.15s, transform 0.1s;
    }
    .send-btn:hover { opacity: 0.9; }
    .send-btn:active { transform: scale(0.94); }
    .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .send-btn svg { width: 18px; height: 18px; fill: white; }

    .powered-by {
      text-align: center;
      font-size: 11px;
      color: #94a3b8;
      padding: 6px;
    }
    .powered-by a { color: inherit; text-decoration: none; }

    @media (max-width: 480px) {
      .window {
        left: 0 !important; right: 0 !important;
        bottom: 0 !important;
        width: 100vw;
        height: 100vh;
        border-radius: 0;
      }
      .bubble { bottom: 16px; right: 16px; }
    }
  `;

  /**
   * Parse inline markdown into a DocumentFragment using safe DOM construction.
   * Only used for bot messages. User messages stay as textContent.
   */
  function parseMarkdown(text) {
    var frag = document.createDocumentFragment();
    var lines = text.split('\n');
    var listItems = [];

    function flushList() {
      if (listItems.length === 0) return;
      var ul = document.createElement('ul');
      for (var i = 0; i < listItems.length; i++) {
        var li = document.createElement('li');
        appendInline(li, listItems[i]);
        ul.appendChild(li);
      }
      frag.appendChild(ul);
      listItems = [];
    }

    function appendInline(parent, str) {
      // Pattern matches: **bold**, *italic*, `code`, [text](url)
      var re = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^)]+)\))/g;
      var last = 0;
      var match;
      while ((match = re.exec(str)) !== null) {
        if (match.index > last) {
          parent.appendChild(document.createTextNode(str.slice(last, match.index)));
        }
        var el;
        if (match[2] !== undefined) {
          el = document.createElement('strong');
          el.textContent = match[2];
        } else if (match[3] !== undefined) {
          el = document.createElement('em');
          el.textContent = match[3];
        } else if (match[4] !== undefined) {
          el = document.createElement('code');
          el.textContent = match[4];
        } else if (match[5] !== undefined && match[6] !== undefined) {
          el = document.createElement('a');
          el.textContent = match[5];
          el.href = match[6];
          el.target = '_blank';
          el.rel = 'noopener noreferrer';
        }
        parent.appendChild(el);
        last = re.lastIndex;
      }
      if (last < str.length) {
        parent.appendChild(document.createTextNode(str.slice(last)));
      }
    }

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      var listMatch = line.match(/^[\-\*] (.+)/);
      if (listMatch) {
        listItems.push(listMatch[1]);
      } else {
        flushList();
        if (i > 0) {
          frag.appendChild(document.createElement('br'));
        }
        appendInline(frag, line);
      }
    }
    flushList();
    return frag;
  }

  // SVG icons
  var CHAT_ICON = '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';
  var CLOSE_ICON = '<svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>';
  var SEND_ICON = '<svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>';

  function createWidget() {
    var host = document.createElement('div');
    host.id = 'chatbot-widget-root';
    var shadow = host.attachShadow({ mode: 'open' });

    shadow.innerHTML = '<style>' + STYLES + '</style>' +
      '<button class="bubble" id="bubble" aria-label="Open chat" title="' + TITLE + '">' +
        CHAT_ICON +
      '</button>' +
      '<div class="window" id="window" role="dialog" aria-label="Chat window" aria-hidden="true">' +
        '<div class="header">' +
          '<div>' +
            '<div class="header-title">' + TITLE + '</div>' +
            '<div class="header-subtitle" id="status-text">Connecting...</div>' +
          '</div>' +
          '<button class="close-btn" id="close-btn" aria-label="Close chat">' + CLOSE_ICON + '</button>' +
        '</div>' +
        '<div class="messages" id="messages" role="log" aria-live="polite"></div>' +
        '<div class="input-area">' +
          '<textarea class="input" id="input" placeholder="Type a message..." rows="1" aria-label="Type your message"></textarea>' +
          '<button class="send-btn" id="send-btn" aria-label="Send message" disabled>' + SEND_ICON + '</button>' +
        '</div>' +
        '<div class="powered-by">Powered by AI</div>' +
      '</div>';

    document.body.appendChild(host);

    var bubble = shadow.getElementById('bubble');
    var win = shadow.getElementById('window');
    var closeBtn = shadow.getElementById('close-btn');
    var input = shadow.getElementById('input');
    var sendBtn = shadow.getElementById('send-btn');
    var messages = shadow.getElementById('messages');
    var statusText = shadow.getElementById('status-text');

    // Open/close
    bubble.addEventListener('click', function() { toggleWindow(true); });
    closeBtn.addEventListener('click', function() { toggleWindow(false); });

    function toggleWindow(open) {
      isOpen = open;
      win.classList.toggle('open', open);
      win.setAttribute('aria-hidden', String(!open));
      bubble.setAttribute('aria-expanded', String(open));

      if (open) {
        input.focus();
        if (!welcomeShown) {
          showWelcome();
        }
        if (!ws || ws.readyState !== WebSocket.OPEN) {
          connectWS();
        }
      }
    }

    // Close on Escape
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen) toggleWindow(false);
    });

    // Input auto-resize + Enter to send
    input.addEventListener('input', function() {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 120) + 'px';
      sendBtn.disabled = !input.value.trim();
    });

    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    sendBtn.addEventListener('click', sendMessage);

    function addMessage(role, content) {
      var el = document.createElement('div');
      el.className = 'msg ' + role;
      if (role === 'bot' && content) {
        el.appendChild(parseMarkdown(content));
      } else {
        el.textContent = content;
      }
      messages.appendChild(el);
      messages.scrollTop = messages.scrollHeight;
      return el;
    }

    function showTyping() {
      var el = document.createElement('div');
      el.className = 'msg bot typing-indicator';
      el.id = 'typing';
      el.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
      messages.appendChild(el);
      messages.scrollTop = messages.scrollHeight;
      return el;
    }

    function removeTyping() {
      var el = shadow.getElementById('typing');
      if (el) el.remove();
    }

    function showWelcome() {
      welcomeShown = true;
      fetch(API_HOST + '/api/v1/chatbots/' + CHATBOT_ID + '/widget-config')
        .then(function(res) {
          if (res.ok) return res.json();
          throw new Error('Config fetch failed');
        })
        .then(function(config) {
          if (config.welcome_message) {
            addMessage('bot', config.welcome_message);
          }
        })
        .catch(function() {
          addMessage('bot', 'Hi! How can I help you today?');
        });
    }

    function sendMessage() {
      var text = input.value.trim();
      if (!text) return;
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        addMessage('bot', 'Connecting... please try again in a moment.');
        connectWS();
        return;
      }

      addMessage('user', text);
      input.value = '';
      input.style.height = 'auto';
      sendBtn.disabled = true;
      input.disabled = true;

      showTyping();
      ws.send(text);
    }

    function connectWS() {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

      var params = new URLSearchParams({ session_id: SESSION_ID });
      if (API_KEY) params.append('api_key', API_KEY);

      var url = WS_HOST + '/ws/chat/' + CHATBOT_ID + '?' + params;
      ws = new WebSocket(url);

      statusText.textContent = 'Connecting...';
      sendBtn.disabled = true;

      ws.onopen = function() {
        statusText.textContent = 'Online';
        sendBtn.disabled = false;
        input.disabled = false;
        reconnectDelay = 1000;

        // Start heartbeat
        if (heartbeatInterval) clearInterval(heartbeatInterval);
        heartbeatInterval = setInterval(function() {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 25000);
      };

      ws.onmessage = function(event) {
        try {
          var data = JSON.parse(event.data);

          if (data.type === 'start') {
            removeTyping();
            currentBotText = '';
            currentBotMessage = addMessage('bot', '');
          } else if (data.type === 'token' && currentBotMessage) {
            currentBotText += data.content;
            currentBotMessage.innerHTML = '';
            currentBotMessage.appendChild(parseMarkdown(currentBotText));
            messages.scrollTop = messages.scrollHeight;
          } else if (data.type === 'end') {
            currentBotMessage = null;
            currentBotText = '';
            sendBtn.disabled = false;
            input.disabled = false;
            input.focus();
          } else if (data.type === 'error') {
            removeTyping();
            addMessage('bot', 'Sorry, something went wrong. Please try again.');
            sendBtn.disabled = false;
            input.disabled = false;
            currentBotMessage = null;
          }
          // pong: heartbeat ok, no action needed
        } catch (e) {
          // non-JSON message, ignore
        }
      };

      ws.onerror = function() {
        statusText.textContent = 'Connection error';
      };

      ws.onclose = function() {
        statusText.textContent = 'Offline';
        sendBtn.disabled = true;
        ws = null;

        // Clear heartbeat
        if (heartbeatInterval) {
          clearInterval(heartbeatInterval);
          heartbeatInterval = null;
        }

        // Exponential backoff reconnect
        if (isOpen) {
          setTimeout(function() { connectWS(); }, reconnectDelay);
          reconnectDelay = Math.min(reconnectDelay * 2, 30000);
        }
      };
    }

    return { toggleWindow: toggleWindow };
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWidget);
  } else {
    createWidget();
  }
})();
