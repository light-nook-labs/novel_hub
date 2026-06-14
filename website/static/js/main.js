// Theme toggle
(function() {
  const toggle = document.getElementById('theme-toggle');
  const sun = document.getElementById('icon-sun');
  const moon = document.getElementById('icon-moon');

  function updateIcons() {
    const isDark = document.documentElement.classList.contains('dark');
    sun.classList.toggle('hidden', !isDark);
    moon.classList.toggle('hidden', isDark);
  }

  function reloadGiscus() {
    if (typeof loadGiscus === 'function') {
      // Small delay to ensure DOM is updated
      setTimeout(loadGiscus, 100);
    }
  }

  updateIcons();

  toggle.addEventListener('click', function() {
    document.documentElement.classList.toggle('dark');
    const isDark = document.documentElement.classList.contains('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateIcons();
    reloadGiscus();
  });
})();

// Mobile menu
document.addEventListener('DOMContentLoaded', function() {
  var menuToggle = document.getElementById('menu-toggle');
  var menuDropdown = document.getElementById('menu-dropdown');
  if (menuToggle && menuDropdown) {
    menuToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      menuDropdown.classList.toggle('hidden');
    });
    document.addEventListener('click', function() {
      menuDropdown.classList.add('hidden');
    });
  }

  var browseMenu = document.getElementById('nav-browse-menu');
  if (browseMenu) {
    document.addEventListener('click', function(e) {
      if (!document.getElementById('nav-browse').contains(e.target)) {
        browseMenu.classList.add('hidden');
      }
    });
  }
});

// Search toggle - inline expandable
document.addEventListener('DOMContentLoaded', function() {
  var searchToggle = document.getElementById('search-toggle');
  var searchForm = document.getElementById('search-form');
  var searchWrap = document.getElementById('search-wrap');
  if (searchToggle && searchForm) {
    searchToggle.addEventListener('click', function(e) {
      e.stopPropagation();
      var isHidden = searchForm.classList.contains('hidden');
      searchForm.classList.toggle('hidden');
      searchToggle.classList.toggle('hidden');
      if (isHidden) {
        searchForm.querySelector('input').focus();
      }
    });
    searchForm.addEventListener('click', function(e) {
      e.stopPropagation();
    });
    document.addEventListener('click', function(e) {
      if (searchWrap && !searchWrap.contains(e.target)) {
        searchForm.classList.add('hidden');
        searchToggle.classList.remove('hidden');
      }
    });
  }
});

// Hero background cache
document.addEventListener('DOMContentLoaded', function() {
  const bg = document.getElementById('hero-bg');
  if (!bg) return;

  const key = 'novel_hub_banner_bg';
  const cached = localStorage.getItem(key);
  const serverUrl = bg.dataset.defaultBg;

  // Always prefer server URL; fall back to cache
  const url = serverUrl || cached;
  if (url) {
    bg.style.backgroundImage = 'url(' + url + ')';
    const img = new Image();
    img.onload = function() {
      localStorage.setItem(key, url);
    };
    img.src = url;
  }
});
