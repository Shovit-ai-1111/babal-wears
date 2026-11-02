(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const motion = (target, values) => {
    if (window.gsap && !reduced.matches) return gsap.to(target, values);
    if (window.gsap) return gsap.set(target, { ...values, duration: 0, delay: 0 });
    values.onComplete?.();
    return null;
  };
  let toastTimer;
  function toast(message) {
    const el = $('#toast');
    if (!el) return;
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 4500);
  }

  // Alpine owns only payment-panel disclosure; the design/canvas engine is vanilla JS.
  document.addEventListener('alpine:init', () => {
    Alpine.data('checkout', () => ({ timing: 'cod', provider: '', init() {
      this.provider = this.$el.querySelector('[name="provider_choice"]')?.value || '';
    } }));
  });
  document.addEventListener('htmx:responseError', event => {
    toast(event.detail.xhr.status === 429 ? 'A few too many attempts. Try again in a few minutes.' : 'That request did not go through. Please try again.');
  });
  document.addEventListener('htmx:sendError', () => toast('Connection interrupted. Please try again.'));
  const cursor = $('#cursor');
  if (cursor && matchMedia('(pointer:fine)').matches) {
    document.addEventListener('pointermove', event => {
      cursor.style.left = `${event.clientX}px`;
      cursor.style.top = `${event.clientY}px`;
      cursor.classList.toggle('visible', !reduced.matches && Boolean(event.target.closest('#wardrobe')));
    });
    document.addEventListener('pointerleave', () => cursor.classList.remove('visible'));
  }

  const dataNode = $('#studio-data');
  if (!dataNode || !$('#rail-track')) return;
  const data = JSON.parse(dataNode.textContent);
  if (!data.colors.length || !data.prints.length) return;
  const state = { color: 0, print: 0, placement: 'center', scale: 100, step: 1, reached: 1 };
  try {
    const saved = JSON.parse(localStorage.getItem('babal-design-v1') || 'null');
    if (saved) {
      state.color = Math.max(0, data.colors.findIndex(c => c.id === saved.color));
      state.print = Math.max(0, data.prints.findIndex(p => p.id === saved.print));
      if (['center', 'chest', 'back'].includes(saved.placement)) state.placement = saved.placement;
      if (Number.isFinite(saved.scale)) state.scale = Math.round(Math.max(60, Math.min(140, saved.scale)) / 5) * 5;
    }
  } catch { /* Storage may be unavailable in private browsing; design still works. */ }
  const money = value => `NPR ${Number(value).toLocaleString('en-NP', { maximumFractionDigits: 2 })}`;
  const currentColor = () => data.colors[state.color];
  const currentPrint = () => data.prints[state.print];
  const unitPrice = () => Number(data.basePrice) + Number(currentColor().extra) + Number(currentPrint().extra);
  const mix = (hex, weight = .25) => {
    const values = hex.match(/[a-f\d]{2}/gi).map(x => parseInt(x, 16));
    const paper = [244, 241, 232];
    return `rgb(${values.map((v, i) => Math.round(v * weight + paper[i] * (1 - weight))).join(',')})`;
  };
  function persist() {
    try { localStorage.setItem('babal-design-v1', JSON.stringify({ color: currentColor().id, print: currentPrint().id, placement: state.placement, scale: state.scale })); } catch {}
  }
  function updatePrice() {
    const quantity = Math.max(1, Math.min(20, Number($('#id_quantity')?.value) || 1));
    $('#dock-price').textContent = money(unitPrice());
    $('#summary-unit').textContent = money(unitPrice());
    $('#summary-quantity').textContent = String(quantity);
    $('#summary-delivery').textContent = money(data.delivery);
    $('#summary-total').textContent = money(unitPrice() * quantity + Number(data.delivery));
  }
  function updateSelection() {
    $$('[data-color]').forEach(el => el.setAttribute('aria-pressed', String(Number(el.dataset.color) === state.color)));
    $$('[data-shirt]').forEach(el => {
      const active = Number(el.dataset.shirt) === state.color;
      el.classList.toggle('focused', active);
      el.setAttribute('aria-pressed', String(active));
    });
    $$('[data-print]').forEach(el => el.setAttribute('aria-pressed', String(Number(el.dataset.print) === state.print)));
    $$('[data-placement]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.placement === state.placement)));
    $('#color-name').textContent = currentColor().name;
    $('#dock-selection').textContent = state.step === 1 ? currentColor().name : `${currentColor().name} / ${currentPrint().name}`;
    $('#view-label').textContent = state.placement === 'back' ? 'BACK VIEW' : 'FRONT VIEW';
    $('#scale-value').textContent = `${state.scale}%`;
    $('#print-scale').value = state.scale;
    $('#reveal-description').textContent = `${currentColor().name} / ${currentPrint().name}`;
    $('#summary-design').textContent = `${currentColor().name} / ${currentPrint().name}`;
    $('#summary-placement').textContent = `${state.placement === 'chest' ? 'Left chest' : state.placement === 'back' ? 'Back' : 'Front center'} · ${state.scale}% scale`;
    $('#order-color').value = currentColor().id;
    $('#order-print').value = currentPrint().id;
    $('#order-placement').value = state.placement;
    $('#order-scale').value = state.scale;
    document.documentElement.style.setProperty('--ambient-color', mix(currentColor().hex, .38));
    updatePrice();
    persist();
    renderPreviews().catch(() => toast('This print could not load. Check your connection or choose another.'));
  }

  // Geometry is shared by the live canvas and exported PNG. Design metadata, not the
  // uploaded preview, is authoritative for production (client images are untrusted).
  const frontPath = 'M171 66L104 91L28 204L103 253L139 201L130 490Q250 515 370 490L361 201L397 253L472 204L396 91L329 66C305 87 288 96 250 96C212 96 195 87 171 66Z';
  const backPath = 'M171 66L104 91L28 204L103 253L139 201L130 490Q250 515 370 490L361 201L397 253L472 204L396 91L329 66C305 75 288 82 250 82C212 82 195 75 171 66Z';
  const loadedImages = new Map();
  function loadPrint(url) {
    if (loadedImages.has(url)) return loadedImages.get(url);
    const promise = new Promise((resolve, reject) => {
      const image = new Image();
      image.decoding = 'async';
      image.onload = () => resolve(image);
      image.onerror = () => { loadedImages.delete(url); reject(new Error('Artwork unavailable')); };
      image.src = url;
    });
    loadedImages.set(url, promise);
    return promise;
  }
  function drawShirt(ctx, artwork) {
    const path = new Path2D(state.placement === 'back' ? backPath : frontPath);
    ctx.save();
    ctx.fillStyle = currentColor().hex;
    ctx.fill(path);
    ctx.save();
    ctx.clip(path);
    const light = ctx.createLinearGradient(80, 120, 430, 410);
    light.addColorStop(0, 'rgba(255,255,255,.21)');
    light.addColorStop(.33, 'rgba(255,255,255,0)');
    light.addColorStop(.68, 'rgba(0,0,0,.045)');
    light.addColorStop(1, 'rgba(0,0,0,.24)');
    ctx.fillStyle = light;
    ctx.fillRect(0, 0, 500, 560);
    for (const [x, width] of [[137, 22], [336, 25]]) {
      const fold = ctx.createLinearGradient(x, 0, x + width, 0);
      fold.addColorStop(0, 'rgba(0,0,0,0)');
      fold.addColorStop(.45, 'rgba(0,0,0,.06)');
      fold.addColorStop(.65, 'rgba(255,255,255,.07)');
      fold.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = fold;
      ctx.fillRect(x, 205, width, 285);
    }
    const side = (state.placement === 'chest' ? 66 : 160) * state.scale / 100;
    const fit = Math.min(side / artwork.naturalWidth, side / artwork.naturalHeight);
    const width = artwork.naturalWidth * fit;
    const height = artwork.naturalHeight * fit;
    const x = state.placement === 'chest' ? 307 : 250;
    const y = state.placement === 'chest' ? 180 : 270;
    ctx.drawImage(artwork, x - width / 2, y - height / 2, width, height);
    ctx.restore();
    ctx.strokeStyle = 'rgba(0,0,0,.12)';
    ctx.lineWidth = 1.1;
    ctx.stroke(path);
    ctx.strokeStyle = 'rgba(0,0,0,.16)';
    ctx.lineWidth = 2;
    ctx.stroke(new Path2D('M141 197L153 468M359 197L347 468M134 479Q250 501 366 479M36 195L109 241M391 241L464 195'));
    ctx.strokeStyle = 'rgba(255,255,255,.16)';
    ctx.lineWidth = 1;
    ctx.stroke(new Path2D('M136 482Q250 504 364 482M39 192L110 238M390 238L461 192'));
    ctx.strokeStyle = 'rgba(0,0,0,.22)';
    ctx.lineWidth = 8;
    ctx.stroke(new Path2D(state.placement === 'back' ? 'M177 66Q250 102 323 66' : 'M179 67Q250 132 321 67'));
    ctx.strokeStyle = 'rgba(255,255,255,.17)';
    ctx.lineWidth = 1.5;
    ctx.stroke(new Path2D(state.placement === 'back' ? 'M177 69Q250 106 323 69' : 'M179 72Q250 138 321 72'));
    if (state.placement !== 'back') {
      ctx.fillStyle = '#e6e2d7';
      ctx.fillRect(239, 98, 22, 12);
      ctx.font = 'bold 7px Inter, sans-serif';
      ctx.fillStyle = '#17191b';
      ctx.textAlign = 'center';
      ctx.fillText('b.', 250, 107);
    }
    ctx.restore();
  }
  let renderGeneration = 0;
  async function renderPreviews() {
    const generation = ++renderGeneration;
    const artwork = await loadPrint(currentPrint().url);
    if (generation !== renderGeneration) return;
    $$('canvas[data-preview]').forEach(canvas => {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.save();
      ctx.scale(canvas.width / 500, canvas.height / 560);
      drawShirt(ctx, artwork);
      ctx.restore();
      canvas.setAttribute('aria-label', `${currentColor().name} T-shirt with ${currentPrint().name}, ${state.placement}, ${state.scale}% size`);
    });
  }
  async function exportCanvas() {
    const artwork = await loadPrint(currentPrint().url);
    if (document.fonts?.ready) await document.fonts.ready;
    const canvas = document.createElement('canvas');
    canvas.width = 1000;
    canvas.height = 1200;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 1000, 1200);
    gradient.addColorStop(0, '#f4f1e8');
    gradient.addColorStop(1, mix(currentColor().hex, .25));
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 1000, 1200);
    ctx.fillStyle = '#d5ff45';
    ctx.beginPath();
    ctx.arc(700, 500, 270, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#17191b';
    ctx.font = '900 35px Inter, sans-serif';
    ctx.fillText('babal / MADE BY YOU', 50, 65);
    ctx.font = '500 16px Inter, sans-serif';
    ctx.fillText(`DESIGN PREVIEW · ${state.placement === 'back' ? 'BACK' : 'FRONT'} VIEW`, 50, 97);
    ctx.save();
    ctx.translate(50, 95);
    ctx.scale(1.8, 1.8);
    ctx.shadowColor = 'rgba(0,0,0,.12)';
    ctx.shadowBlur = 12;
    ctx.shadowOffsetY = 12;
    const silhouette = new Path2D(state.placement === 'back' ? backPath : frontPath);
    ctx.fillStyle = currentColor().hex;
    ctx.fill(silhouette);
    ctx.shadowColor = 'transparent';
    drawShirt(ctx, artwork);
    ctx.restore();
    ctx.fillStyle = '#17191b';
    ctx.font = '700 25px Inter, sans-serif';
    ctx.fillText(`${currentColor().name} / ${currentPrint().name}`, 50, 1100, 900);
    ctx.font = '400 18px Inter, sans-serif';
    ctx.fillText(`${state.placement.toUpperCase()} · ${state.scale}% PRINT SCALE · @babalwears`, 50, 1135);
    ctx.font = '400 13px Inter, sans-serif';
    ctx.fillText('Digital mockup. Confirm garment color and print dimensions before production.', 50, 1170);
    return canvas;
  }
  async function designBlob() {
    const canvas = await exportCanvas();
    return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('Could not create your PNG.')), 'image/png'));
  }
  function download(blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'my-babal-tee.png';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  $('#download-design').addEventListener('click', async event => {
    const button = event.currentTarget;
    button.disabled = true;
    try { download(await designBlob()); toast('Saved. Good taste looks good on you.'); }
    catch { toast('Your design could not be saved. Please try again.'); }
    finally { button.disabled = false; }
  });
  $('#share-design').addEventListener('click', async () => {
    try {
      const blob = await designBlob();
      const file = new File([blob], 'my-babal-tee.png', { type: 'image/png' });
      if (navigator.share && navigator.canShare?.({ files: [file] })) await navigator.share({ files: [file], title: 'I made it babal.', text: 'My custom BABAL WEARS tee.' });
      else { download(blob); toast('PNG saved — share it with your people.'); }
    } catch (error) { if (error.name !== 'AbortError') toast('Sharing is unavailable. Use Save your design to download the PNG.'); }
  });

  const rail = $('#wardrobe');
  const track = $('#rail-track');
  const garments = $$('[data-shirt]');
  const position = { x: 0 };
  let drag = null;
  let ignoreClickUntil = 0;
  let wheelTimer;
  const targetFor = index => rail.clientWidth * .40 - (garments[index].offsetLeft + garments[index].offsetWidth / 2);
  const clampX = value => Math.max(targetFor(garments.length - 1), Math.min(targetFor(0), value));
  function applyPosition() {
    track.style.transform = `translate3d(${position.x}px,0,0)`;
  }
  function nearest() {
    let index = 0;
    let distance = Infinity;
    garments.forEach((el, i) => {
      const delta = Math.abs(position.x - targetFor(i));
      if (delta < distance) { distance = delta; index = i; }
    });
    return index;
  }
  function focusColor(index, animate = true) {
    state.color = (index + data.colors.length) % data.colors.length;
    updateSelection();
    if (window.gsap) gsap.killTweensOf(position);
    const target = targetFor(state.color);
    if (animate && !reduced.matches && window.gsap) {
      gsap.to(position, { x: target, duration: .65, ease: 'power3.out', onUpdate: applyPosition });
      sway(2);
    } else { position.x = target; applyPosition(); }
  }
  function sway(velocity) {
    if (!window.gsap || reduced.matches) return;
    const shirts = $$('.shirt-svg', track);
    gsap.killTweensOf(shirts);
    gsap.to(shirts, { rotation: Math.max(-8, Math.min(8, velocity * 3)), duration: .12, overwrite: true,
      onComplete: () => gsap.to(shirts, { rotation: 0, duration: 1.15, ease: 'elastic.out(1,.35)', stagger: .025 }) });
  }
  rail.addEventListener('pointerdown', event => {
    if (event.button !== 0 && event.pointerType === 'mouse') return;
    if (window.gsap) gsap.killTweensOf(position);
    drag = { id: event.pointerId, startX: event.clientX, startY: event.clientY, base: position.x, lastX: event.clientX, time: performance.now(), velocity: 0, started: false };
  });
  rail.addEventListener('pointermove', event => {
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.started) {
      if (Math.abs(dy) > Math.abs(dx) && Math.abs(dy) > 10) { drag = null; return; }
      if (Math.abs(dx) < 6) return;
      drag.started = true;
      rail.setPointerCapture(event.pointerId);
      rail.classList.add('dragging');
    }
    const now = performance.now();
    const elapsed = Math.max(1, now - drag.time);
    drag.velocity = .65 * drag.velocity + .35 * ((event.clientX - drag.lastX) / elapsed);
    drag.lastX = event.clientX;
    drag.time = now;
    position.x = clampX(drag.base + dx);
    applyPosition();
    if (nearest() !== state.color) { state.color = nearest(); updateSelection(); }
    if (window.gsap && !reduced.matches) gsap.to($$('.shirt-svg', track), { rotation: Math.max(-8, Math.min(8, drag.velocity * 4)), duration: .18, overwrite: true });
  });
  function release(event) {
    if (!drag || drag.id !== event.pointerId) return;
    const prior = drag;
    drag = null;
    rail.classList.remove('dragging');
    if (rail.hasPointerCapture(event.pointerId)) rail.releasePointerCapture(event.pointerId);
    if (!prior.started) return;
    ignoreClickUntil = performance.now() + 350;
    const velocity = performance.now() - prior.time > 120 ? 0 : prior.velocity;
    const target = clampX(position.x + velocity * 210);
    sway(velocity);
    if (window.gsap && !reduced.matches) gsap.to(position, { x: target, duration: .65, ease: 'power3.out', onUpdate() {
      applyPosition();
      if (nearest() !== state.color) { state.color = nearest(); updateSelection(); }
    }, onComplete: () => focusColor(nearest()) });
    else focusColor(nearest(), false);
  }
  rail.addEventListener('pointerup', release);
  rail.addEventListener('pointercancel', release);
  rail.addEventListener('wheel', event => {
    if (event.ctrlKey) return;
    const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
    const next = clampX(position.x - delta);
    // At either end, hand vertical scrolling back to the page.
    if (Math.abs(next - position.x) < .5) return;
    event.preventDefault();
    if (window.gsap) gsap.killTweensOf(position);
    position.x = next;
    applyPosition();
    const index = nearest();
    if (index !== state.color) { state.color = index; updateSelection(); }
    sway(-delta / 30);
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(() => focusColor(nearest()), 170);
  }, { passive: false });
  rail.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); focusColor(state.color + (event.key === 'ArrowRight' ? 1 : -1)); }
    if (event.key === 'Home') { event.preventDefault(); focusColor(0); }
    if (event.key === 'End') { event.preventDefault(); focusColor(garments.length - 1); }
  });
  $$('[data-color]').forEach(el => el.addEventListener('click', () => focusColor(Number(el.dataset.color))));
  garments.forEach(el => el.addEventListener('click', () => { if (performance.now() > ignoreClickUntil) focusColor(Number(el.dataset.shirt)); }));
  $('#rail-prev').addEventListener('click', () => focusColor(state.color - 1));
  $('#rail-next').addEventListener('click', () => focusColor(state.color + 1));
  const resizeObserver = new ResizeObserver(() => { if (state.step === 1) focusColor(state.color, false); });
  resizeObserver.observe(rail);
  $$('[data-print]').forEach(el => el.addEventListener('click', () => { state.print = Number(el.dataset.print); updateSelection(); }));
  $$('[data-placement]').forEach(el => el.addEventListener('click', () => { state.placement = el.dataset.placement; updateSelection(); }));
  $('#print-scale').addEventListener('input', event => { state.scale = Number(event.target.value); updateSelection(); });
  $('#id_quantity').addEventListener('input', updatePrice);

  let transitioning = false;
  const nextLabels = ["", "That's my color", "Reveal my tee", "Let's make it real"];
  const stepLabels = ['', 'YOUR FIRST GOOD DECISION', 'A LITTLE PERSONALITY GOES A LONG WAY', 'LOOKING VERY YOU'];
  async function goTo(step) {
    if (transitioning || step < 1 || step > 4 || step > state.reached + 1) return;
    transitioning = true;
    let clone = null;
    try {
      await renderPreviews();
      if (state.step === 1 && step === 2 && window.gsap && !reduced.matches) {
        const source = $('.shirt-svg', garments[state.color]);
        const rect = source.getBoundingClientRect();
        clone = source.cloneNode(true);
        $('.hanger', clone)?.remove();
        Object.assign(clone.style, { position: 'fixed', left: `${rect.left}px`, top: `${rect.top}px`, width: `${rect.width}px`, height: `${rect.height}px`, maxWidth: 'none', zIndex: '40', pointerEvents: 'none', filter: 'drop-shadow(12px 20px 14px #0002)' });
        document.body.append(clone);
      }
      state.step = step;
      state.reached = Math.max(state.reached, step);
      $$('.scene').forEach(scene => { scene.hidden = Number(scene.dataset.step) !== step; });
      $$('.stepper [data-goto]').forEach(button => {
        const n = Number(button.dataset.goto);
        button.disabled = n > state.reached;
        if (n === step) button.setAttribute('aria-current', 'step'); else button.removeAttribute('aria-current');
      });
      $('#journey-back').hidden = step === 1;
      $('#journey-dock').hidden = step === 4;
      if (step < 4) { $('#journey-next').firstChild.textContent = `${nextLabels[step]} `; $('#dock-step').textContent = stepLabels[step]; }
      updateSelection();
      const scene = $(`[data-step="${step}"]`);
      const heading = $('h1', scene);
      heading.focus({ preventScroll: true });
      const studioTop = $('#studio').getBoundingClientRect().top + window.scrollY;
      if (window.scrollY > studioTop + 80) window.scrollTo({ top: studioTop, behavior: 'instant' });
      if (step === 1) focusColor(state.color, false);
      if (clone) {
        const canvas = $('#print-canvas');
        const rect = canvas.getBoundingClientRect();
        canvas.style.opacity = '0';
        await new Promise(resolve => gsap.timeline({ onComplete: resolve })
          .to(clone, { rotation: -8, y: -20, duration: .16 })
          .to(clone, { left: rect.left, top: rect.top, width: rect.width, height: rect.height, rotation: 0, y: 0, duration: .55, ease: 'power3.inOut' })
          .to(clone, { opacity: 0, duration: .18 })
          .to(canvas, { opacity: 1, duration: .18 }, '<'));
        clone.remove();
        clone = null;
      } else if (step !== 3) motion(scene, { opacity: 1, y: 0, startAt: { opacity: .3, y: 12 }, duration: .45, ease: 'power2.out' });
      if (step === 3) {
        motion($('.reveal-canvas-wrap'), { rotationY: 360, scale: 1, rotation: 0, startAt: { rotationY: 130, scale: .82, rotation: -5 }, duration: 1.1, ease: 'power3.out' });
        motion($('.design-ticket'), { y: 0, opacity: 1, startAt: { y: 25, opacity: 0 }, delay: .55, duration: .4 });
      }
      if (step === 4) $('#checkout-preview').src = (await exportCanvas()).toDataURL('image/png');
    } catch { toast('The preview is still loading. Please try again.'); }
    finally { clone?.remove(); $('#print-canvas').style.opacity = '1'; transitioning = false; }
  }
  $('#journey-next').addEventListener('click', () => goTo(state.step + 1));
  $('#journey-back').addEventListener('click', () => goTo(state.step - 1));
  $$('[data-goto]').forEach(button => button.addEventListener('click', () => goTo(Number(button.dataset.goto))));

  const form = $('#order-form');
  const errorsBox = $('#order-errors');
  const submit = $('#submit-order');
  const phone = $('#id_phone');
  phone.addEventListener('input', () => phone.setCustomValidity(''));
  phone.addEventListener('blur', () => {
    let value = phone.value.replace(/[०-९]/g, digit => '०१२३४५६७८९'.indexOf(digit)).replace(/[\s()-]/g, '').replace(/^(\+977|977(?=\d{10}$))/, '');
    phone.setCustomValidity(value && !/^9[678]\d{8}$/.test(value) ? 'Enter a 10-digit Nepali mobile number starting with 96, 97 or 98.' : '');
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submit.disabled) return;
    errorsBox.hidden = true;
    $$('[aria-invalid]', form).forEach(el => el.removeAttribute('aria-invalid'));
    const upload = $('#id_payment_screenshot');
    if (!upload.disabled && upload.files[0]?.size > 5 * 1024 * 1024) { toast('Payment screenshot must be smaller than 5 MB.'); upload.focus(); return; }
    submit.disabled = true;
    submit.textContent = 'Making it official…';
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45000);
    try {
      const body = new FormData(form);
      body.set('design_image', await designBlob(), 'my-babal-tee.png');
      const response = await fetch(form.action, { method: 'POST', body, credentials: 'same-origin', headers: { Accept: 'application/json' }, signal: controller.signal });
      const contentType = response.headers.get('content-type') || '';
      const result = contentType.includes('application/json') ? await response.json() : null;
      if (response.ok && result?.redirect) { window.location.assign(result.redirect); return; }
      const errors = result?.errors || { request: [{ message: response.status === 429 ? 'Too many attempts. Please wait a few minutes.' : response.status === 403 ? 'Your session expired. Reload the page before submitting again.' : response.status === 413 ? 'The upload is too large. Use smaller images.' : 'Something went wrong. Please try again; duplicate submissions will not create another order.' }] };
      errorsBox.replaceChildren();
      const title = document.createElement('strong');
      title.textContent = 'A few details need another look:';
      const list = document.createElement('ul');
      for (const [field, messages] of Object.entries(errors)) {
        const input = form.elements.namedItem(field);
        if (input?.setAttribute) input.setAttribute('aria-invalid', 'true');
        messages.forEach(error => { const item = document.createElement('li'); item.textContent = error.message; list.append(item); });
      }
      errorsBox.append(title, list);
      errorsBox.hidden = false;
      errorsBox.focus();
    } catch {
      errorsBox.textContent = 'Connection interrupted. Check your connection and submit again. If the order reached us, the same order will be returned.';
      errorsBox.hidden = false;
      errorsBox.focus();
    } finally {
      clearTimeout(timeout);
      submit.disabled = false;
      submit.textContent = 'Make it official ↗';
    }
  });
  focusColor(state.color, false);
})();
