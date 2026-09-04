/* ── Wrencher · main.js ───────────────────────────────────────────────── */

// Mobile nav toggle
const hamburger = document.querySelector('.nav__hamburger');
const navLinks  = document.querySelector('.nav__links');
if (hamburger && navLinks) {
  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
  });
  navLinks.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => navLinks.classList.remove('open'));
  });
}

// FAQ accordion
document.querySelectorAll('.faq__q').forEach(btn => {
  btn.addEventListener('click', () => {
    const item = btn.closest('.faq__item');
    const isOpen = item.classList.contains('open');
    document.querySelectorAll('.faq__item').forEach(i => i.classList.remove('open'));
    if (!isOpen) item.classList.add('open');
  });
});

// Contact form (Web3Forms)
const form = document.getElementById('contact-form');
if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = form.querySelector('[type=submit]');
    btn.disabled = true;
    btn.textContent = 'Sending…';
    try {
      const res = await fetch('https://api.web3forms.com/submit', {
        method: 'POST',
        body: new FormData(form),
      });
      if (res.ok) {
        // Hide form, show success message outside the form
        form.style.display = 'none';
        const success = document.getElementById('form-success');
        if (success) {
          success.style.display = 'block';
        }
      } else {
        btn.disabled = false;
        btn.textContent = 'Send message';
        alert('Something went wrong. Please email us directly at hello@wrencher.app');
      }
    } catch {
      btn.disabled = false;
      btn.textContent = 'Send message';
      alert('Something went wrong. Please email us directly at hello@wrencher.app');
    }
  });
}
