/* AP Invoice Anomaly Detector -- JavaScript */

(function () {
    'use strict';

    function _basePath() {
        var m = window.location.pathname.match(/^(\/preview\/[^/]+)/);
        return m ? m[1] : '';
    }

    // ── Theme toggle ──────────────────────────────────────
    var themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function () {
            var html = document.documentElement;
            var current = html.getAttribute('data-theme') || 'light';
            var next = current === 'light' ? 'dark' : 'light';
            html.setAttribute('data-theme', next);

            fetch(_basePath() + '/api/theme', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: next })
            }).catch(function () { /* best effort */ });
        });
    }

    // ── Help panel ────────────────────────────────────────
    var helpToggle = document.getElementById('helpToggle');
    var helpClose = document.getElementById('helpClose');
    var helpPanel = document.getElementById('helpPanel');
    var helpOverlay = document.getElementById('helpOverlay');

    function openHelp() {
        if (helpPanel) helpPanel.classList.add('open');
        if (helpOverlay) helpOverlay.classList.add('open');
    }
    function closeHelp() {
        if (helpPanel) helpPanel.classList.remove('open');
        if (helpOverlay) helpOverlay.classList.remove('open');
    }

    if (helpToggle) helpToggle.addEventListener('click', openHelp);
    if (helpClose) helpClose.addEventListener('click', closeHelp);
    if (helpOverlay) helpOverlay.addEventListener('click', closeHelp);

    // ── Auto-dismiss flash messages ───────────────────────
    var flashes = document.querySelectorAll('.flash');
    flashes.forEach(function (el) {
        setTimeout(function () {
            el.style.opacity = '0';
            el.style.transition = 'opacity 0.3s';
            setTimeout(function () { el.remove(); }, 300);
        }, 5000);
    });
})();
