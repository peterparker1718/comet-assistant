// Comet Assistant — Main JS

// Mark current nav link
(function () {
  const links = document.querySelectorAll('.nav-links a');
  const path = window.location.pathname.split('/').pop() || 'index.html';
  links.forEach(link => {
    const href = link.getAttribute('href');
    if (href === path || (path === '' && href === 'index.html')) {
      link.setAttribute('aria-current', 'page');
    }
  });
})();

// Form submission handler (demo)
const form = document.querySelector('.contact-form');
if (form) {
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    const original = btn.textContent;
    btn.textContent = 'Sending...';
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = 'Message Sent!';
      form.reset();
      setTimeout(() => {
        btn.textContent = original;
        btn.disabled = false;
      }, 3000);
    }, 1200);
  });
}

// Animate terminal typing effect on intelligence page
const terminalBody = document.querySelector('.terminal-body');
if (terminalBody) {
  const lines = terminalBody.querySelectorAll('.line');
  lines.forEach((line, i) => {
    line.style.opacity = '0';
    line.style.transform = 'translateX(-8px)';
    setTimeout(() => {
      line.style.transition = 'opacity 0.3s, transform 0.3s';
      line.style.opacity = '1';
      line.style.transform = 'translateX(0)';
    }, i * 180);
  });
}

// Intersection Observer for fade-in cards
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.card').forEach(card => {
  card.style.opacity = '0';
  card.style.transform = 'translateY(20px)';
  card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
  observer.observe(card);
});
