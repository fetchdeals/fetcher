document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#search-form');
  const sortPriceBtn = document.querySelector('#sort-price');
  const sortTotalBtn = document.querySelector('#sort-total');
  const sortFvsBtn = document.querySelector('#sort-fvs');
  const simplifyBtn = document.querySelector('#simplify');
  const countrySelect = document.querySelector('#country-lang');
  const countryInput = document.querySelector('#country');
  let results = document.querySelectorAll('.result-row');
  const loadMoreBtn = document.querySelector('#load-more');
  const pageInput = document.querySelector('#page');

  // Auto-detect UK location
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${position.coords.latitude}&longitude=${position.coords.longitude}&localityLanguage=en`)
          .then(res => res.json())
          .then(data => {
            const country = data.countryCode === 'GB' ? 'UK' : 'UK';
            countryInput.value = country;
            countrySelect.value = `${country}-en`;
          })
          .catch(() => {
            countryInput.value = 'UK';
            countrySelect.value = 'UK-en';
          });
      },
      () => {
        countryInput.value = 'UK';
        countrySelect.value = 'UK-en';
      }
    );
  } else {
    countryInput.value = 'UK';
    countrySelect.value = 'UK-en';
  }

  if (countrySelect) {
    countrySelect.addEventListener('change', () => {
      const [country, lang] = countrySelect.value.split('-');
      countryInput.value = country;
    });
  }

  if (form) {
    form.addEventListener('submit', (e) => {
      const query = form.querySelector('input[name="query"]').value.trim();
      if (!query) {
        e.preventDefault();
        alert('Please enter a product!');
      }
    });
  }

  function sortResults(key, order = 'asc') {
    const container = document.querySelector('.results-table tbody');
    if (!container) return;
    const rows = Array.from(results);
    rows.sort((a, b) => {
      const aVal = parseFloat(a.dataset[key]);
      const bVal = parseFloat(b.dataset[key]);
      return order === 'asc' ? aVal - bVal : bVal - aVal;
    });
    container.innerHTML = '';
    rows.forEach(row => container.appendChild(row));
    results = document.querySelectorAll('.result-row');
    [sortPriceBtn, sortTotalBtn, sortFvsBtn, simplifyBtn].forEach(btn => btn?.classList.remove('text-blue-600', 'font-bold'));
    if (key === 'price' && sortPriceBtn) sortPriceBtn.classList.add('text-blue-600', 'font-bold');
    if (key === 'total' && sortTotalBtn) sortTotalBtn.classList.add('text-blue-600', 'font-bold');
    if (key === 'fvs' && sortFvsBtn) sortFvsBtn.classList.add('text-blue-600', 'font-bold');
  }

  function simplifyResults() {
    const container = document.querySelector('.results-table tbody');
    if (!container) return;
    const rows = Array.from(results).sort((a, b) => parseFloat(b.dataset.fvs) - parseFloat(a.dataset.fvs)).slice(0, 5);
    container.innerHTML = '';
    rows.forEach(row => container.appendChild(row));
    results = document.querySelectorAll('.result-row');
    [sortPriceBtn, sortTotalBtn, sortFvsBtn].forEach(btn => btn?.classList.remove('text-blue-600', 'font-bold'));
    if (simplifyBtn) simplifyBtn.classList.add('text-blue-600', 'font-bold');
  }

  if (sortPriceBtn) {
    sortPriceBtn.addEventListener('click', () => sortResults('price'));
  }

  if (sortTotalBtn) {
    sortTotalBtn.addEventListener('click', () => sortResults('total'));
  }

  if (sortFvsBtn) {
    sortFvsBtn.addEventListener('click', () => sortResults('fvs', 'desc'));
  }

  if (simplifyBtn) {
    simplifyBtn.addEventListener('click', simplifyResults);
  }

  if (loadMoreBtn && pageInput) {
    loadMoreBtn.addEventListener('click', () => {
      const currentPage = parseInt(pageInput.value);
      pageInput.value = currentPage + 1;
      form.submit();
    });
  }

  document.querySelectorAll('.shop-btn, .result-link, .alert-btn').forEach(link => {
    link.addEventListener('click', () => {
      let url = link.href || link.dataset.url;
      if (url.includes('amazon.co.uk') && !url.includes('addToCart')) {
        url += '&addToCart=1'; // Extend Amazon cookie to 90 days
      }
      const retailer = link.dataset.retailer;
      const action = link.classList.contains('alert-btn') ? 'alert_set' : 'click';
      fetch('/analytics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: 'anon_' + Date.now(),
          ref: new URLSearchParams(window.location.search).get('ref') || 'none',
          url,
          retailer,
          action,
          category: link.dataset.category || 'general',
          savings: parseFloat(link.dataset.price || 0),
          subId: link.dataset.subId || 'none',
          timestamp: new Date().toISOString()
        })
      }).catch(e => console.error('Track error:', e));
    });
  });
});