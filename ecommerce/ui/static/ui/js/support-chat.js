(() => {
  const widget = document.querySelector('[data-support-chat]');
  if (!widget) return;

  const toggle = widget.querySelector('[data-chat-toggle]');
  const panel = widget.querySelector('.support-chat__panel');
  const close = widget.querySelector('[data-chat-close]');
  const form = widget.querySelector('[data-chat-form]');
  const input = form.querySelector('input[name="message"]');
  const sendButton = form.querySelector('button[type="submit"]');
  const log = widget.querySelector('[data-chat-messages]');
  const status = widget.querySelector('[data-chat-status]');
  const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]').value;
  const conversation = [];

  const addMessage = (text, role) => {
    const message = document.createElement('div');
    message.className = `support-chat__message support-chat__message--${role}`;
    message.textContent = text;
    log.appendChild(message);
    log.scrollTop = log.scrollHeight;
  };

  const setOpen = (open) => {
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    if (open) input.focus();
  };

  toggle.addEventListener('click', () => setOpen(panel.hidden));
  close.addEventListener('click', () => setOpen(false));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    conversation.push({ role: 'user', content: text });
    addMessage(text, 'user');
    input.value = '';
    input.disabled = true;
    sendButton.disabled = true;
    status.textContent = 'Upsteps is replying…';

    try {
      const response = await fetch(widget.dataset.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ messages: conversation }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Support chat is temporarily unavailable.');

      conversation.push({ role: 'assistant', content: result.reply });
      addMessage(result.reply, 'assistant');
      status.textContent = '';
    } catch (error) {
      conversation.pop();
      addMessage(error.message, 'assistant');
      status.textContent = '';
    } finally {
      input.disabled = false;
      sendButton.disabled = false;
      input.focus();
    }
  });
})();
