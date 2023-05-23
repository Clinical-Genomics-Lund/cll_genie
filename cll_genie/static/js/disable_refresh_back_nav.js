// Disable refresh
if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
    window.onbeforeunload = function () {
        window.history.replaceState(null, null, window.location.href);
    };
}

// Disable back navigation
history.pushState(null, null, document.URL);
window.addEventListener('popstate', function () {
    history.pushState(null, null, document.URL);
});