import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const WIDGET_SRC = readFileSync(
  resolve(__dirname, '../src/chatbot.js'),
  'utf-8'
);

/**
 * Replicate parseMarkdown for unit testing.
 * The widget bundles this inside an IIFE, so we define it here as a standalone
 * copy for direct testing. This is the source of truth — if the widget's
 * parseMarkdown changes, these tests should be updated to match.
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

/**
 * Load the widget into jsdom by injecting a mock script tag.
 */
function loadWidget() {
  // Clean up any previous widget
  const existing = document.getElementById('chatbot-widget-root');
  if (existing) existing.remove();

  // Create a fake script element with required data attributes
  const script = document.createElement('script');
  script.setAttribute('data-chatbot-id', 'test-bot-123');
  script.setAttribute('data-api-key', 'cbk_test');
  script.setAttribute('data-title', 'Test Bot');
  script.src = 'http://localhost:8000/widget/chatbot.min.js';
  document.body.appendChild(script);

  // Stub WebSocket
  const wsSendSpy = vi.fn();
  const wsInstances = [];
  globalThis.WebSocket = vi.fn(function () {
    const instance = {
      readyState: 1,
      send: wsSendSpy,
      close: vi.fn(),
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
    };
    wsInstances.push(instance);
    // Auto-trigger onopen after microtask
    Promise.resolve().then(() => {
      if (instance.onopen) instance.onopen();
    });
    return instance;
  });
  globalThis.WebSocket.OPEN = 1;
  globalThis.WebSocket.CONNECTING = 0;

  // Stub sessionStorage
  const storage = {};
  vi.stubGlobal('sessionStorage', {
    getItem: (k) => storage[k] || null,
    setItem: (k, v) => {
      storage[k] = v;
    },
  });

  // Stub fetch for welcome message
  globalThis.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ welcome_message: 'Hello!' }),
    })
  );

  // Override document.currentScript to our mock script
  Object.defineProperty(document, 'currentScript', {
    value: script,
    writable: true,
    configurable: true,
  });

  // Execute the widget IIFE
  const fn = new Function(WIDGET_SRC);
  fn();

  const host = document.getElementById('chatbot-widget-root');
  return { host, shadow: host?.shadowRoot, wsSendSpy, wsInstances };
}

// ---- parseMarkdown unit tests ----

describe('parseMarkdown', () => {
  function render(text) {
    const frag = parseMarkdown(text);
    const div = document.createElement('div');
    div.appendChild(frag);
    return div;
  }

  it('renders plain text as text node', () => {
    const el = render('hello world');
    expect(el.textContent).toBe('hello world');
    expect(el.children.length).toBe(0);
  });

  it('renders **bold** as <strong>', () => {
    const el = render('this is **bold** text');
    const strong = el.querySelector('strong');
    expect(strong).not.toBeNull();
    expect(strong.textContent).toBe('bold');
    expect(el.textContent).toBe('this is bold text');
  });

  it('renders *italic* as <em>', () => {
    const el = render('this is *italic* text');
    const em = el.querySelector('em');
    expect(em).not.toBeNull();
    expect(em.textContent).toBe('italic');
  });

  it('renders `code` as <code>', () => {
    const el = render('use `npm install` here');
    const code = el.querySelector('code');
    expect(code).not.toBeNull();
    expect(code.textContent).toBe('npm install');
  });

  it('renders [text](url) as <a> with safe attributes', () => {
    const el = render('click [here](https://example.com) now');
    const a = el.querySelector('a');
    expect(a).not.toBeNull();
    expect(a.textContent).toBe('here');
    expect(a.href).toBe('https://example.com/');
    expect(a.target).toBe('_blank');
    expect(a.rel).toBe('noopener noreferrer');
  });

  it('rejects non-http URLs in links', () => {
    const el = render('click [xss](javascript:alert(1)) now');
    const a = el.querySelector('a');
    expect(a).toBeNull();
  });

  it('renders list items as <ul><li>', () => {
    const el = render('- item one\n- item two\n- item three');
    const ul = el.querySelector('ul');
    expect(ul).not.toBeNull();
    const items = ul.querySelectorAll('li');
    expect(items.length).toBe(3);
    expect(items[0].textContent).toBe('item one');
    expect(items[2].textContent).toBe('item three');
  });

  it('renders * list items as <ul><li>', () => {
    const el = render('* first\n* second');
    const items = el.querySelectorAll('li');
    expect(items.length).toBe(2);
    expect(items[0].textContent).toBe('first');
  });

  it('renders newlines as <br>', () => {
    const el = render('line one\nline two');
    const brs = el.querySelectorAll('br');
    expect(brs.length).toBe(1);
  });

  it('handles mixed inline formatting', () => {
    const el = render('**bold** and *italic* and `code`');
    expect(el.querySelector('strong').textContent).toBe('bold');
    expect(el.querySelector('em').textContent).toBe('italic');
    expect(el.querySelector('code').textContent).toBe('code');
  });

  it('handles empty string', () => {
    const el = render('');
    expect(el.textContent).toBe('');
  });
});

// ---- Widget integration tests ----

describe('Widget', () => {
  let shadow, wsSendSpy;

  beforeEach(() => {
    document.body.innerHTML = '';
    vi.restoreAllMocks();
    const result = loadWidget();
    shadow = result.shadow;
    wsSendSpy = result.wsSendSpy;
  });

  it('creates shadow DOM on initialization', () => {
    const host = document.getElementById('chatbot-widget-root');
    expect(host).not.toBeNull();
    expect(host.shadowRoot).not.toBeNull();
  });

  it('renders bubble button', () => {
    const bubble = shadow.getElementById('bubble');
    expect(bubble).not.toBeNull();
    expect(bubble.tagName).toBe('BUTTON');
  });

  it('chat window starts hidden', () => {
    const win = shadow.getElementById('window');
    expect(win.classList.contains('open')).toBe(false);
    expect(win.getAttribute('aria-hidden')).toBe('true');
  });

  it('bubble click opens chat window', () => {
    const bubble = shadow.getElementById('bubble');
    const win = shadow.getElementById('window');
    bubble.click();
    expect(win.classList.contains('open')).toBe(true);
    expect(win.getAttribute('aria-hidden')).toBe('false');
  });

  it('close button closes chat window', () => {
    const bubble = shadow.getElementById('bubble');
    const win = shadow.getElementById('window');
    const closeBtn = shadow.getElementById('close-btn');

    bubble.click();
    expect(win.classList.contains('open')).toBe(true);

    closeBtn.click();
    expect(win.classList.contains('open')).toBe(false);
  });

  it('send button is initially disabled', () => {
    const sendBtn = shadow.getElementById('send-btn');
    expect(sendBtn.disabled).toBe(true);
  });

  it('typing in input enables send button', () => {
    const input = shadow.getElementById('input');
    const sendBtn = shadow.getElementById('send-btn');

    input.value = 'hello';
    input.dispatchEvent(new Event('input'));
    expect(sendBtn.disabled).toBe(false);
  });

  it('Enter key submits message', async () => {
    const bubble = shadow.getElementById('bubble');
    bubble.click();
    // Wait for WS onopen
    await new Promise((r) => setTimeout(r, 10));

    const input = shadow.getElementById('input');
    const msgContainer = shadow.getElementById('messages');

    input.value = 'test message';
    input.dispatchEvent(new Event('input'));

    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));

    // User message should appear
    const userMsg = msgContainer.querySelector('.msg.user');
    expect(userMsg).not.toBeNull();
    expect(userMsg.textContent).toBe('test message');
  });

  it('user messages render as plain text (no HTML injection)', async () => {
    const bubble = shadow.getElementById('bubble');
    bubble.click();
    await new Promise((r) => setTimeout(r, 10));

    const input = shadow.getElementById('input');
    const msgContainer = shadow.getElementById('messages');

    input.value = '<img src=x onerror=alert(1)>';
    input.dispatchEvent(new Event('input'));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));

    const userMsg = msgContainer.querySelector('.msg.user');
    expect(userMsg.textContent).toBe('<img src=x onerror=alert(1)>');
    expect(userMsg.querySelector('img')).toBeNull();
  });

  it('bot welcome message renders', async () => {
    const bubble = shadow.getElementById('bubble');
    bubble.click();

    // Wait for welcome message fetch
    await new Promise((r) => setTimeout(r, 50));

    const msgContainer = shadow.getElementById('messages');
    const botMsgs = msgContainer.querySelectorAll('.msg.bot');
    expect(botMsgs.length).toBeGreaterThan(0);
  });
});
