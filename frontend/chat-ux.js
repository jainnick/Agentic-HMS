const $ = (selector, root = document) => root.querySelector(selector);
const panel = $('#panel');
const chat = $('#chat');
const launcher = $('#launcher');
const closeButton = $('#close');
const input = $('#chatInput');
const send = $('#send');
const header = panel ? $('.phead', panel) : null;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

if (panel && chat && launcher && closeButton && input && send) {
  const friendlyTools = {
    knowledge_search: 'Searched hotel knowledge',
    room_availability: 'Checked live room availability',
    room_booking: 'Reservation action completed',
    create_room_hold: 'Held the selected room',
    room_hold: 'Held the selected room',
  };

  function updateComposer() {
    send.disabled = !input.value.trim();
  }

  function scrollToLatest(behavior = 'smooth') {
    requestAnimationFrame(() => {
      chat.scrollTo({
        top: chat.scrollHeight,
        behavior: reducedMotion.matches ? 'auto' : behavior,
      });
    });
  }

  function enterPanel() {
    if (panel.classList.contains('hidden')) return;
    const wasOpen = document.body.classList.contains('chat-panel-open');
    document.body.classList.add('chat-panel-open');
    launcher.setAttribute('aria-expanded', 'true');
    panel.setAttribute('aria-hidden', 'false');
    panel.classList.remove('chat-leave');
    if (!wasOpen) {
      panel.classList.add('chat-enter');
      if (!reducedMotion.matches) {
        setTimeout(() => panel.classList.remove('chat-enter'), 380);
      }
    }
  }

  function finishClose() {
    panel.classList.add('hidden');
    panel.classList.remove('chat-leave', 'chat-enter', 'chat-dragging');
    panel.style.removeProperty('transform');
    panel.style.removeProperty('opacity');
    panel.style.removeProperty('transition');
    document.body.classList.remove('chat-panel-open');
    launcher.setAttribute('aria-expanded', 'false');
    panel.setAttribute('aria-hidden', 'true');
    launcher.focus({ preventScroll: true });
  }

  function closePanelAnimated() {
    if (panel.classList.contains('hidden')) return;
    panel.classList.remove('chat-enter');
    if (reducedMotion.matches) {
      finishClose();
      return;
    }
    panel.classList.add('chat-leave');
    setTimeout(finishClose, 230);
  }

  // The existing app owns open actions. Observe the class it changes and add motion/a11y state.
  const panelStateObserver = new MutationObserver(() => {
    if (!panel.classList.contains('hidden')) {
      enterPanel();
    } else if (!panel.classList.contains('chat-leave')) {
      document.body.classList.remove('chat-panel-open');
      launcher.setAttribute('aria-expanded', 'false');
      panel.setAttribute('aria-hidden', 'true');
    }
  });
  panelStateObserver.observe(panel, { attributes: true, attributeFilter: ['class'] });

  launcher.setAttribute('aria-expanded', 'false');
  launcher.setAttribute('aria-controls', 'panel');
  panel.setAttribute('aria-hidden', panel.classList.contains('hidden') ? 'true' : 'false');

  // Override only closing so the panel can animate before display:none is applied.
  closeButton.addEventListener('click', event => {
    event.preventDefault();
    event.stopImmediatePropagation();
    closePanelAnimated();
  }, true);

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.classList.contains('hidden')) {
      event.preventDefault();
      closePanelAnimated();
    }
  }, true);

  // Add a lightweight typing state around only the guest chat request.
  const nativeFetch = window.fetch.bind(window);
  let typingNode = null;
  function showTyping() {
    if (typingNode || panel.classList.contains('hidden')) return;
    typingNode = document.createElement('div');
    typingNode.className = 'chat-typing';
    typingNode.setAttribute('role', 'status');
    typingNode.setAttribute('aria-label', 'Concierge is responding');
    typingNode.innerHTML = '<i></i><i></i><i></i>';
    chat.appendChild(typingNode);
    scrollToLatest();
  }
  function hideTyping() {
    if (!typingNode) return;
    typingNode.remove();
    typingNode = null;
  }

  window.fetch = async (...args) => {
    const request = args[0];
    const url = typeof request === 'string' ? request : request?.url || '';
    const isWidgetChat = /\/api\/v1\/widget\/[^/]+\/chat(?:\?|$)/.test(url);
    if (!isWidgetChat) return nativeFetch(...args);
    showTyping();
    try {
      return await nativeFetch(...args);
    } finally {
      hideTyping();
    }
  };

  // Make current backend traces and grounding metadata read as user-facing status surfaces.
  function enhanceNode(node) {
    if (!(node instanceof Element)) return;

    const tools = node.matches('.tool') ? [node] : [...node.querySelectorAll('.tool')];
    tools.forEach(tool => {
      const raw = tool.textContent.trim();
      const normalized = raw.toLowerCase();
      tool.textContent = friendlyTools[normalized] || normalized
        .replaceAll('_', ' ')
        .replace(/^./, value => value.toUpperCase());
      tool.setAttribute('role', 'status');
    });

    const sources = node.matches('.source') ? [node] : [...node.querySelectorAll('.source')];
    sources.forEach(source => {
      source.textContent = source.textContent.replace(/^Source\s*·\s*/i, '').trim();
      source.setAttribute('title', 'Answer source');
    });
  }

  [...chat.children].forEach(enhanceNode);
  const chatObserver = new MutationObserver(records => {
    records.forEach(record => record.addedNodes.forEach(enhanceNode));
    scrollToLatest();
  });
  chatObserver.observe(chat, { childList: true, subtree: true });

  chat.addEventListener('scroll', () => {
    panel.classList.toggle('chat-scrolled', chat.scrollTop > 4);
  }, { passive: true });

  input.addEventListener('input', updateComposer);
  input.addEventListener('focus', () => scrollToLatest('auto'));
  updateComposer();

  // Drag the sheet down to dismiss. This is intentionally UI-only and does not touch chat state.
  if (header) {
    let dragging = false;
    let startY = 0;
    let currentY = 0;
    let lastY = 0;
    let lastTime = 0;
    let velocity = 0;

    header.addEventListener('pointerdown', event => {
      if (event.target.closest('button')) return;
      dragging = true;
      startY = event.clientY;
      currentY = 0;
      lastY = event.clientY;
      lastTime = performance.now();
      velocity = 0;
      header.setPointerCapture(event.pointerId);
      panel.classList.remove('chat-enter', 'chat-leave');
      panel.classList.add('chat-dragging');
      panel.style.transition = 'none';
    });

    header.addEventListener('pointermove', event => {
      if (!dragging) return;
      const now = performance.now();
      const dt = Math.max(now - lastTime, 1);
      velocity = (event.clientY - lastY) / dt * 1000;
      lastY = event.clientY;
      lastTime = now;
      currentY = Math.max(-18, event.clientY - startY);
      const y = currentY < 0 ? currentY * 0.22 : currentY;
      const progress = Math.min(Math.max(y / Math.max(panel.clientHeight, 1), 0), 1);
      const scale = 1 - progress * 0.035;
      panel.style.transform = `translateY(${y}px) scale(${scale})`;
      panel.style.opacity = String(1 - progress * 0.35);
    });

    function releaseDrag() {
      if (!dragging) return;
      dragging = false;
      panel.classList.remove('chat-dragging');
      const shouldDismiss = currentY > panel.clientHeight * 0.28 || velocity > 650;
      if (shouldDismiss) {
        panel.style.transition = reducedMotion.matches ? 'none' : 'transform 180ms ease, opacity 180ms ease';
        panel.style.transform = `translateY(${panel.clientHeight + 48}px) scale(.96)`;
        panel.style.opacity = '0';
        setTimeout(finishClose, reducedMotion.matches ? 0 : 185);
        return;
      }
      panel.style.transition = reducedMotion.matches ? 'none' : 'transform 300ms cubic-bezier(.2,.85,.25,1), opacity 220ms ease';
      panel.style.transform = 'translateY(0) scale(1)';
      panel.style.opacity = '1';
      setTimeout(() => {
        panel.style.removeProperty('transition');
        panel.style.removeProperty('transform');
        panel.style.removeProperty('opacity');
      }, reducedMotion.matches ? 0 : 310);
    }

    header.addEventListener('pointerup', releaseDrag);
    header.addEventListener('pointercancel', releaseDrag);
  }
}
