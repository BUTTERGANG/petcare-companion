// PetCare Companion — UI polish layer
// Toasts, form loading states, delete confirmations

(function () {
  'use strict';

  // ---------- Toasts ----------
  // Usage: showToast('Saved!', 'success' | 'error' | 'info')
  window.showToast = function (message, type) {
    type = type || 'success';
    var colors = {
      success: 'bg-paw-600',
      error: 'bg-red-600',
      info: 'bg-gray-800 dark:bg-gray-700'
    };
    var icons = { success: '✓', error: '✕', info: 'ℹ' };

    // container
    var container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'fixed bottom-20 md:bottom-6 right-4 z-[100] flex flex-col gap-2 items-end';
      document.body.appendChild(container);
    }

    var toast = document.createElement('div');
    toast.className = 'flex items-center gap-3 px-4 py-3 rounded-xl text-white text-sm font-medium shadow-lift transition-all duration-300 opacity-0 translate-y-2 ' + colors[type];
    toast.setAttribute('role', 'status');
    toast.innerHTML =
      '<span class="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-xs">' + (icons[type] || '✓') + '</span>' +
      '<span>' + message + '</span>';
    container.appendChild(toast);

    requestAnimationFrame(function () {
      toast.classList.remove('opacity-0', 'translate-y-2');
    });
    setTimeout(function () {
      toast.classList.add('opacity-0', 'translate-y-2');
      setTimeout(function () { toast.remove(); }, 300);
    }, 2600);
  };
  window.toast = window.showToast;

  // ---------- Flash messages from server redirects (?saved=1 etc.) ----------
  function flashFromQuery() {
    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get('saved') === '1') { window.showToast('Saved'); }
      if (params.get('deleted') === '1') { window.showToast('Deleted', 'info'); }
    } catch (e) {}
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', flashFromQuery);
  } else { flashFromQuery(); }

  // ---------- Form loading states ----------
  // On submit: disable button, show spinner text
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.dataset.noLoading === 'true') return;

    var btn = form.querySelector('button[type="submit"]');
    if (!btn || btn.disabled) return;

    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.classList.add('opacity-70', 'cursor-wait');
    btn.innerHTML = '<span class="inline-flex items-center gap-2"><span class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>' + btn.dataset.originalText + '</span>';

    // Safety: re-enable after 8s in case navigation stalls
    setTimeout(function () {
      btn.disabled = false;
      btn.classList.remove('opacity-70', 'cursor-wait');
      if (btn.dataset.originalText) btn.textContent = btn.dataset.originalText;
    }, 8000);
  }, true);

  // ---------- Delete confirmation styling ----------
  // Upgrade native confirm() with a styled modal
  var pendingDeleteForm = null;
  document.addEventListener('click', function (e) {
    var t = e.target;
    // intercept submit-button clicks on forms with confirm attribute
    var form = t.closest && t.closest('form[onsubmit^="return confirm"]');
    if (!form) return;
    e.preventDefault();
    e.stopPropagation();
    showConfirm(form);
  }, true);

  function showConfirm(form) {
    pendingDeleteForm = form;
    var msgMatch = form.getAttribute('onsubmit').match(/confirm\('([^']+)'\)/);
    var msg = msgMatch ? msgMatch[1] : 'Are you sure?';

    var overlay = document.createElement('div');
    overlay.id = 'confirm-overlay';
    overlay.className = 'fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm';
    overlay.innerHTML =
      '<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-lift max-w-sm w-full p-6 transform scale-95 opacity-0 transition-all duration-200">' +
      '  <div class="flex items-start gap-3">' +
      '    <span class="w-10 h-10 rounded-full bg-red-100 dark:bg-red-950/60 flex items-center justify-center text-xl shrink-0">🗑️</span>' +
      '    <div>' +
      '      <h3 class="font-semibold text-gray-900 dark:text-white">Delete</h3>' +
      '      <p class="text-sm text-gray-500 mt-1">' + msg.replace(/Delete |delete /, '') + ' This can\'t be undone.</p>' +
      '    </div>' +
      '  </div>' +
      '  <div class="flex gap-2 justify-end mt-5">' +
      '    <button data-act="cancel" class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 rounded-lg">Cancel</button>' +
      '    <button data-act="ok" class="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg">Delete</button>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(overlay);

    requestAnimationFrame(function () {
      var box = overlay.firstElementChild;
      box.classList.remove('scale-95', 'opacity-0');
    });

    overlay.addEventListener('click', function (ev) {
      var act = ev.target.getAttribute && ev.target.getAttribute('data-act');
      if (act === 'ok') {
        close();
        // strip the onsubmit guard and resubmit programmatically
        form.removeAttribute('onsubmit');
        form.dataset.noLoading = 'true';
        if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); }
      } else if (act === 'cancel' || ev.target === overlay) {
        close();
      }
    });

    document.addEventListener('keydown', function esc(ev) {
      if (ev.key === 'Escape') { close(); document.removeEventListener('keydown', esc); }
    });

    function close() {
      var box = overlay.firstElementChild;
      box.classList.add('scale-95', 'opacity-0');
      setTimeout(function () { overlay.remove(); }, 180);
    }
  }

  // ---------- Skeleton helper ----------
  // Adds .skeleton shimmer to elements with [data-skeleton] while images load
  document.querySelectorAll('img[data-skeleton]').forEach(function (img) {
    if (img.complete) return;
    img.style.opacity = '0';
    var wrap = img.parentElement;
    if (wrap) wrap.classList.add('animate-pulse', 'bg-gray-200', 'dark:bg-gray-800');
    img.addEventListener('load', function () {
      img.style.transition = 'opacity .3s';
      img.style.opacity = '1';
      if (wrap) wrap.classList.remove('animate-pulse', 'bg-gray-200', 'dark:bg-gray-800');
    });
  });
})();