function handleBannerError(img) {
  var title = img.alt;
  var div = document.createElement('div');
  div.className = 'h-full bg-gradient-to-r from-amber-300 to-orange-300 flex items-center justify-center';
  var span = document.createElement('span');
  span.className = 'text-gray-800 text-lg font-bold';
  span.textContent = title;
  div.appendChild(span);
  img.parentElement.replaceChild(div, img);
}

// Banners lightbox
(function() {
  const lightbox = document.getElementById('lightbox');
  const img = document.getElementById('lightbox-img');
  let currentIndex = -1;
  let items = [];

  function getItems() {
    return document.querySelectorAll('[data-src]');
  }

  window.openLightbox = function(el) {
    items = getItems();
    currentIndex = Array.from(items).indexOf(el);
    img.src = el.dataset.src;
    lightbox.classList.remove('hidden');
    lightbox.classList.add('flex');
    document.body.style.overflow = 'hidden';
  };

  window.closeLightbox = function(e) {
    if (e && e.target !== lightbox && !e.target.closest('button')) return;
    lightbox.classList.add('hidden');
    lightbox.classList.remove('flex');
    document.body.style.overflow = '';
    currentIndex = -1;
  };

  function navigate(direction) {
    if (currentIndex < 0 || !items.length) return;
    currentIndex = (currentIndex + direction + items.length) % items.length;
    img.src = items[currentIndex].dataset.src;
  }

  document.addEventListener('keydown', function(e) {
    if (lightbox.classList.contains('hidden')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') navigate(-1);
    if (e.key === 'ArrowRight') navigate(1);
  });
})();
