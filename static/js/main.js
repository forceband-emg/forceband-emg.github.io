/* ============================================================
   ForceBand — page interactions
   Scroll progress, reveal animations, scroll-triggered video
   playback, counters, lightbox, and small UI helpers.
   ============================================================ */

(function () {
  'use strict';

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- nav: progress bar, shadow, burger, active link ---------- */

  const progressBar = document.getElementById('progressBar');
  const nav = document.getElementById('siteNav');
  const toTop = document.getElementById('toTop');

  function onScroll() {
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const y = window.scrollY;
    progressBar.style.width = (max > 0 ? (y / max) * 100 : 0) + '%';
    nav.classList.toggle('scrolled', y > 8);
    toTop.classList.toggle('show', y > 900);
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  toTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: reducedMotion ? 'auto' : 'smooth' });
  });

  const burger = document.getElementById('navBurger');
  const navLinks = document.getElementById('navLinks');

  burger.addEventListener('click', () => {
    const open = navLinks.classList.toggle('open');
    burger.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', String(open));
  });

  navLinks.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') {
      navLinks.classList.remove('open');
      burger.classList.remove('open');
      burger.setAttribute('aria-expanded', 'false');
    }
  });

  // Highlight the nav link of the section currently in view.
  const sections = [...document.querySelectorAll('main section[id]')];
  const linkFor = {};
  navLinks.querySelectorAll('a[href^="#"]').forEach((a) => {
    linkFor[a.getAttribute('href').slice(1)] = a;
  });

  const sectionSpy = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const link = linkFor[entry.target.id];
        if (!link) return;
        if (entry.isIntersecting) {
          navLinks.querySelectorAll('a').forEach((a) => a.classList.remove('active'));
          link.classList.add('active');
        }
      });
    },
    { rootMargin: '-35% 0px -60% 0px' }
  );

  sections.forEach((s) => sectionSpy.observe(s));

  /* ---------- reveal-on-scroll with sibling stagger ---------- */

  const revealEls = [...document.querySelectorAll('.reveal')];

  // Stagger siblings that reveal together (cards in the same grid).
  const groups = new Map();
  revealEls.forEach((el) => {
    const parent = el.parentElement;
    if (!groups.has(parent)) groups.set(parent, 0);
    const i = groups.get(parent);
    el.style.setProperty('--d', Math.min(i * 0.08, 0.4) + 's');
    groups.set(parent, i + 1);
  });

  if (reducedMotion) {
    revealEls.forEach((el) => el.classList.add('in'));
  } else {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('in');
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -4% 0px' }
    );
    revealEls.forEach((el) => revealObserver.observe(el));
  }

  /* ---------- scroll-triggered video playback ---------- */

  const scrollVideos = [...document.querySelectorAll('video.scroll-play')];

  // Load lazily: attach the real src shortly before the video scrolls in.
  const loader = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const v = entry.target;
        if (v.dataset.src && !v.src) {
          v.src = v.dataset.src;
          v.load();
        }
        loader.unobserve(v);
      });
    },
    { rootMargin: '700px 0px' }
  );

  // Play while sufficiently visible, pause when scrolled away.
  // Per-video visibility via data-threshold (default 0.25); capped by what is
  // achievable when the video is taller than the viewport.
  const player = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        const v = entry.target;
        const want = parseFloat(v.dataset.threshold || '0.25');
        const viewH = entry.rootBounds ? entry.rootBounds.height : window.innerHeight;
        const cap = Math.min(1, (viewH / entry.boundingClientRect.height) * 0.95);
        const need = Math.min(want, cap);
        if (entry.intersectionRatio >= need) {
          if (v.dataset.src && !v.src) {
            v.src = v.dataset.src;
            v.load();
          }
          const p = v.play();
          if (p) p.catch(() => {});
        } else {
          v.pause();
        }
      });
    },
    { threshold: [0, 0.1, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95, 1] }
  );

  scrollVideos.forEach((v) => {
    loader.observe(v);
    player.observe(v);
  });

  /* ---------- play-once "rest" videos (data-rest = "end" | seconds) ---------- */
  // Instead of looping, settle on a frame after playing through: "end" holds the
  // final frame; a number holds that timestamp. A fresh replay (e.g. scrolling
  // back into view) restarts from the top and then re-settles. A manual scrub
  // cancels the auto-restart so the user's chosen position is respected.

  document.querySelectorAll('video[data-rest]').forEach((v) => {
    const restTime = v.dataset.rest === 'end' ? null : parseFloat(v.dataset.rest);
    let settled = false;
    let selfSeek = false;

    v.addEventListener('ended', () => {
      settled = true;
      if (restTime != null && isFinite(restTime) && v.duration) {
        selfSeek = true;
        try { v.currentTime = Math.min(restTime, v.duration); } catch (_) {}
      }
    });
    v.addEventListener('seeked', () => {
      if (selfSeek) selfSeek = false;  // our own settle-seek: keep "settled"
      else settled = false;            // manual scrub cancels the restart
    });
    v.addEventListener('play', () => {
      if (settled) {
        settled = false;
        try { v.currentTime = 0; } catch (_) {}
      }
    });
  });

  /* ---------- animated counters ---------- */

  const counters = [...document.querySelectorAll('.count')];

  function animateCount(el) {
    const target = parseFloat(el.dataset.count || '0');
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const duration = 1400;
    const start = performance.now();

    function tick(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = (target * eased).toFixed(decimals);
      if (t < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }

  if (reducedMotion) {
    counters.forEach((el) => {
      el.textContent = parseFloat(el.dataset.count || '0').toFixed(
        parseInt(el.dataset.decimals || '0', 10)
      );
    });
  } else {
    const countObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            animateCount(entry.target);
            countObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.6 }
    );
    counters.forEach((el) => countObserver.observe(el));
  }

  /* ---------- start-at offset for click-to-play videos ---------- */
  // Retry across media events until the seek actually sticks: a single
  // loadedmetadata seek can get clamped to 0 if that time isn't seekable yet.

  document.querySelectorAll('video[data-start]').forEach((v) => {
    const start = parseFloat(v.dataset.start);
    if (!start) return;
    let done = false;
    const trySeek = () => {
      if (done || v.readyState < 1) return;
      if (v.currentTime >= start - 0.25) { done = true; return; }
      try { v.currentTime = start; } catch (e) { /* not seekable yet */ }
      if (v.currentTime >= start - 0.25) done = true;
    };
    ['loadedmetadata', 'loadeddata', 'canplay', 'play', 'playing', 'progress'].forEach((ev) =>
      v.addEventListener(ev, trySeek)
    );
    trySeek();
  });

  /* ---------- montage sound toggle ---------- */

  const muteToggle = document.getElementById('muteToggle');
  if (muteToggle) {
    const video = muteToggle.parentElement.querySelector('video');
    const icoMuted = muteToggle.querySelector('.ico-muted');
    const icoSound = muteToggle.querySelector('.ico-sound');

    muteToggle.addEventListener('click', () => {
      video.muted = !video.muted;
      icoMuted.style.display = video.muted ? '' : 'none';
      icoSound.style.display = video.muted ? 'none' : '';
      muteToggle.setAttribute('aria-label', video.muted ? 'Unmute video' : 'Mute video');
      if (!video.muted) {
        const p = video.play();
        if (p) p.catch(() => {});
      }
    });
  }

  /* ---------- horizontal scroller ---------- */

  const skills = document.getElementById('skillsScroll');
  document.querySelectorAll('.hbtn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const dir = parseInt(btn.dataset.dir, 10);
      const card = skills.querySelector('.rollout');
      const step = card ? card.getBoundingClientRect().width + 18 : 360;
      skills.scrollBy({ left: dir * step, behavior: reducedMotion ? 'auto' : 'smooth' });
    });
  });

  /* ---------- lightbox for figures ---------- */

  const lightbox = document.getElementById('lightbox');
  const lightboxImg = lightbox.querySelector('img');

  document.querySelectorAll('img.zoomable').forEach((img) => {
    img.addEventListener('click', () => {
      lightboxImg.src = img.src;
      lightboxImg.alt = img.alt || '';
      lightbox.classList.add('open');
      document.body.style.overflow = 'hidden';
    });
  });

  function closeLightbox() {
    lightbox.classList.remove('open');
    document.body.style.overflow = '';
  }

  lightbox.addEventListener('click', closeLightbox);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightbox.classList.contains('open')) closeLightbox();
  });

  /* ---------- copy BibTeX ---------- */

  const copyBtn = document.getElementById('copyBib');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const text = document.getElementById('bibText').textContent;
      try {
        await navigator.clipboard.writeText(text);
      } catch {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
      }
      copyBtn.classList.add('copied');
      copyBtn.querySelector('span').textContent = 'Copied!';
      setTimeout(() => {
        copyBtn.classList.remove('copied');
        copyBtn.querySelector('span').textContent = 'Copy';
      }, 1800);
    });
  }

  /* ---------- one-at-a-time gallery carousel ---------- */
  // Side arrows + bottom segment bar switch between clips. Only the active video
  // plays; this owns lazy-loading and playback (its videos skip the .scroll-play
  // system), and pauses everything when the gallery scrolls out of view.

  const gallery = document.getElementById('pretrainGallery');
  if (gallery) {
    const slides = [...gallery.querySelectorAll('.gallery-slide')];
    const thumbs = [...gallery.querySelectorAll('.gallery-thumb')];
    const prevBtn = gallery.querySelector('.gallery-arrow.prev');
    const nextBtn = gallery.querySelector('.gallery-arrow.next');
    const labelEl = gallery.querySelector('.gallery-label');
    let idx = 0;
    let inView = false;

    const videoOf = (s) => s.querySelector('video');

    function ensureSrc(s) {
      const v = videoOf(s);
      if (v && v.dataset.src && !v.src) { v.src = v.dataset.src; v.load(); }
      return v;
    }

    function playActive() {
      const v = ensureSrc(slides[idx]);
      if (v) { const p = v.play(); if (p) p.catch(() => {}); }
      ensureSrc(slides[(idx + 1) % slides.length]); // warm up the next clip
    }

    function show(i) {
      idx = (i + slides.length) % slides.length;
      slides.forEach((s, k) => {
        const active = k === idx;
        s.classList.toggle('is-active', active);
        if (!active) { const v = videoOf(s); if (v) v.pause(); }
      });
      thumbs.forEach((t, k) => t.classList.toggle('is-active', k === idx));
      if (labelEl) labelEl.textContent = slides[idx].dataset.label || '';
      if (inView) playActive();
    }

    prevBtn.addEventListener('click', () => show(idx - 1));
    nextBtn.addEventListener('click', () => show(idx + 1));
    thumbs.forEach((t, k) => t.addEventListener('click', () => show(k)));

    gallery.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); show(idx - 1); prevBtn.focus(); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); show(idx + 1); nextBtn.focus(); }
    });

    const galleryIO = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          inView = entry.isIntersecting;
          if (inView) playActive();
          else slides.forEach((s) => { const v = videoOf(s); if (v) v.pause(); });
        });
      },
      { threshold: 0.4 }
    );
    galleryIO.observe(gallery);

    show(0);
  }
})();
