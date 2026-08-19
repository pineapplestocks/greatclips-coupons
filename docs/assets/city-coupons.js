(function () {
  var PAGE = window.__GC_PAGE__;
  var box = document.getElementById('liveCoupons');
  if (!box || !PAGE) return;

  function couponStates(c) {
    return c.coupon_states || (c.coupon_state ? [c.coupon_state] : []);
  }

  function reaches(c) {
    if (c.scope === 'national') return true;
    if (c.scope === 'state') return couponStates(c).indexOf(PAGE.state) !== -1;
    if (c.city_keys && c.city_keys.indexOf(PAGE.cityKey) !== -1) return true;
    if (c.metro_keys && c.metro_keys.indexOf(PAGE.metroKey) !== -1) return true;
    return false;
  }

  function scopeLabel(c) {
    if (c.scope === 'national') return 'Valid at participating US salons';
    if (c.scope === 'state') {
      var states = couponStates(c);
      return states.length > 1
        ? 'Valid across ' + states.join(', ')
        : 'Valid across ' + PAGE.state;
    }
    if (c.scope === 'salon') return 'Salon-specific offer';
    var names = c.market_names || [];
    return names.length ? 'Valid across the ' + names.join(' & ') + ' market'
                        : 'Regional offer';
  }

  function card(c) {
    var el = document.createElement('a');
    el.href = c.url;
    el.target = '_blank';
    el.rel = 'nofollow noopener';
    el.className = 'block bg-white rounded-xl border border-slate-200 p-5 ' +
                   'hover:border-purple-400 hover:shadow-md transition-all';
    var expiry = c.expiration
      ? '<p class="text-xs text-slate-400 mt-2">Expires ' + c.expiration + '</p>' : '';
    el.innerHTML =
      '<div class="flex items-start justify-between gap-4">' +
        '<div>' +
          '<div class="text-2xl font-extrabold text-purple-600">' + (c.price || '') + '</div>' +
          '<p class="text-sm text-slate-600 mt-1">' + scopeLabel(c) + '</p>' + expiry +
        '</div>' +
        '<span class="shrink-0 bg-purple-600 text-white text-sm font-semibold ' +
        'rounded-lg px-4 py-2">Get coupon</span>' +
      '</div>';
    return el;
  }

  fetch('/data/coupons.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (feed) {
      var hits = (feed.coupons || []).filter(reaches);
      if (!hits.length) {
        box.innerHTML =
          '<p class="text-slate-600">No live coupon is verified for ' + PAGE.cityLabel +
          ' right now. National offers appear here as soon as they are found - ' +
          '<a class="text-purple-600 underline" href="/">check every current coupon</a>.</p>';
        return;
      }
      box.innerHTML = '';
      var grid = document.createElement('div');
      grid.className = 'grid gap-4 sm:grid-cols-2';
      hits.slice(0, 8).forEach(function (c) { grid.appendChild(card(c)); });
      box.appendChild(grid);

      var note = document.createElement('p');
      note.className = 'text-xs text-slate-500 mt-4';
      note.textContent = 'Showing ' + Math.min(hits.length, 8) + ' of ' + hits.length +
        ' offers that reach ' + PAGE.cityLabel + '. Verified ' +
        (feed.scraped_at || '').slice(0, 10) + '.';
      box.appendChild(note);
    })
    .catch(function () {
      box.innerHTML =
        '<p class="text-slate-600"><a class="text-purple-600 underline" href="/">' +
        'View all current Great Clips coupons</a>.</p>';
    });
})();
