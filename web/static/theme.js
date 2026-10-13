/* Applied before the stylesheet; appearance changes never rebuild workspace content. */
(function (root) {
  'use strict';
  function createTheme(environment) {
    const document = environment.document;
    const media = environment.matchMedia?.('(prefers-color-scheme: dark)');
    const valid = value => ['system', 'light', 'dark'].includes(value);
    let preference = 'system';
    try {
      const stored = environment.localStorage.getItem('litbeacon-theme');
      if (valid(stored)) preference = stored;
    } catch (_) { /* Private browsing may disable storage. */ }
    function apply() {
      document.documentElement.dataset.theme = preference === 'system'
        ? (media?.matches ? 'dark' : 'light') : preference;
      const control = document.getElementById('theme');
      if (control) control.value = preference;
    }
    function set(value) {
      preference = valid(value) ? value : 'system';
      try { environment.localStorage.setItem('litbeacon-theme', preference); } catch (_) {}
      apply();
    }
    media?.addEventListener('change', () => { if (preference === 'system') apply(); });
    apply();
    document.addEventListener('DOMContentLoaded', () => {
      apply();
      document.getElementById('theme')?.addEventListener('change', event => set(event.target.value));
    }, {once: true});
    return {set, get preference() { return preference; }};
  }
  if (typeof module === 'object' && module.exports) module.exports = createTheme;
  else root.LitTheme = createTheme(root);
})(typeof window !== 'undefined' ? window : globalThis);
