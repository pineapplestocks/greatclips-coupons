var GC_MODAL_HTML = "    <div id=\"gcEmailModal\" class=\"hidden fixed inset-0 z-50 flex items-center justify-center p-4\">\n        <div class=\"absolute inset-0 bg-black/60 backdrop-blur-sm\" onclick=\"gcCloseModal()\"></div>\n        <div class=\"relative bg-white rounded-2xl shadow-2xl max-w-md w-full p-8\">\n            <button onclick=\"gcCloseModal()\" aria-label=\"Close\"\n                    class=\"absolute top-4 right-4 text-slate-400 hover:text-slate-600 text-2xl\">&times;</button>\n\n            <div id=\"gcFormView\">\n                <div class=\"text-center mb-6\">\n                    <div class=\"inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-violet-500 to-purple-500 rounded-full mb-4\">\n                        <span class=\"text-3xl\">&#9986;</span>\n                    </div>\n                    <h3 class=\"text-2xl font-bold text-slate-900\">Get Your Coupon!</h3>\n                    <p class=\"text-slate-600 mt-2\">Enter your email and we&rsquo;ll send the coupon link instantly.</p>\n                    <p id=\"gcModalSalon\" class=\"text-sm font-medium text-purple-600 mt-3\"></p>\n                </div>\n                <form onsubmit=\"gcSubmitEmail(event)\" class=\"space-y-4\">\n                    <input type=\"email\" id=\"gcEmailInput\" placeholder=\"Enter your email\" required\n                           class=\"w-full px-4 py-3 border-2 border-slate-200 rounded-xl focus:border-purple-500 focus:outline-none transition-colors\">\n                    <button type=\"submit\" id=\"gcSubmitBtn\"\n                            class=\"w-full bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-bold py-3 px-6 rounded-xl transition-all shadow-lg shadow-purple-200\">\n                        Send Me the Coupon &#128231;\n                    </button>\n                </form>\n                <button onclick=\"gcSkipEmail()\"\n                        class=\"w-full mt-3 text-slate-500 hover:text-slate-700 text-sm py-2 transition-colors\">\n                    No thanks, just show me the coupon\n                </button>\n                <p class=\"text-center text-xs text-slate-400 mt-4\">\n                    &#128274; No spam, unsubscribe anytime. We respect your privacy.\n                </p>\n            </div>\n\n            <div id=\"gcSuccessView\" class=\"hidden text-center\">\n                <div class=\"inline-flex items-center justify-center w-20 h-20 bg-green-100 rounded-full mb-5\">\n                    <span class=\"text-4xl\">&#10003;</span>\n                </div>\n                <h3 class=\"text-2xl font-bold text-slate-900 mb-2\">Coupon ready!</h3>\n                <p class=\"text-slate-600 mb-1\">A copy was also sent to:</p>\n                <p class=\"font-semibold text-purple-600 mb-5\" id=\"gcSuccessEmail\"></p>\n                <button onclick=\"gcOpenCoupon()\"\n                        class=\"w-full bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-700 hover:to-purple-700 text-white font-bold py-3 px-6 rounded-xl transition-all\">\n                    Open my coupon &rarr;\n                </button>\n            </div>\n        </div>\n    </div>\n";

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
    var el = document.createElement('button');
    el.type = 'button';
    el.className = 'block w-full text-left bg-white rounded-xl border border-slate-200 p-5 ' +
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
        'rounded-lg px-4 py-2">Get Coupon</span>' +
      '</div>';
    // Route through the email capture rather than straight out to the offer.
    el.addEventListener('click', function () { gcOpenModal(c, null); });
    return el;
  }

  // Reveal a "Get Coupon" button on each salon, now that we know an offer reaches
  // this city. Each one carries its own street and ZIP into the signup.
  function wireSalonButtons(best) {
    var buttons = document.querySelectorAll('.gc-salon-coupon');
    for (var i = 0; i < buttons.length; i++) {
      (function (btn) {
        if (!best) return;
        btn.textContent = 'Get Coupon' + (best.price ? ' \u2013 ' + best.price : '');
        btn.hidden = false;
        btn.classList.remove('hidden');
        btn.addEventListener('click', function () {
          gcOpenModal(best, {
            street: btn.getAttribute('data-street') || '',
            zip: btn.getAttribute('data-zip') || ''
          });
        });
      })(buttons[i]);
    }
  }

  // The nationwide section is already in the page's static HTML with its price;
  // all that is missing is the live offer link behind its button.
  function wireNationalButton(coupons) {
    var btn = document.getElementById('gcNationalBtn');
    if (!btn) return;
    var national = null;
    for (var i = 0; i < coupons.length; i++) {
      if (coupons[i].scope === 'national') { national = coupons[i]; break; }
    }
    if (!national) {
      btn.disabled = true;
      btn.textContent = 'Nationwide coupon not available right now';
      btn.className = 'bg-slate-200 text-slate-500 font-semibold py-2.5 px-5 rounded-xl';
      return;
    }
    btn.addEventListener('click', function () { gcOpenModal(national, null); });
  }

  fetch('/data/coupons.json', { cache: 'no-cache' })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
    .then(function (feed) {
      wireNationalButton(feed.coupons || []);
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
      wireSalonButtons(hits[0]);

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

// --- email capture -------------------------------------------------------
// Same contract as the homepage: POST to the worker, which stores the signup and
// mails the coupon through Brevo. Skipping is still allowed so a reader who does
// not want to hand over an address is not stranded.
var GC_WORKER_URL = 'https://greatclips-email.mehulchaudhari.workers.dev';
var gcPending = null;
var gcPendingSalon = null;
var gcModalReady = false;

// Subscribers arriving from a campaign link (?subscribed=1) already gave us
// their email. Remember that so no visit re-gates them.
try {
  if (new URLSearchParams(location.search).get('subscribed') === '1') {
    localStorage.setItem('gcd_subscribed', '1');
  }
} catch (e) {}

function gcIsSubscriber() {
  try { return localStorage.getItem('gcd_subscribed') === '1'; } catch (e) { return false; }
}

// Built on first use so the markup ships once in this file, not on every page.
function gcEnsureModal() {
  if (gcModalReady || document.getElementById('gcEmailModal')) {
    gcModalReady = true;
    return;
  }
  var host = document.createElement('div');
  host.innerHTML = GC_MODAL_HTML;
  document.body.appendChild(host);
  gcModalReady = true;
}

function gcOpenModal(coupon, salon) {
  if (gcIsSubscriber()) {
    if (coupon && coupon.url) window.open(coupon.url, '_blank', 'noopener');
    return;
  }
  if (!coupon || !coupon.url) return;
  gcEnsureModal();
  gcPending = coupon;
  gcPendingSalon = salon;

  var page = window.__GC_PAGE__ || {};
  var label = document.getElementById('gcModalSalon');
  if (label) {
    label.textContent = salon && salon.street
      ? coupon.price + ' at Great Clips, ' + salon.street + ', ' + page.cityLabel
      : (coupon.price || '') + ' – ' + (page.cityLabel || '');
  }

  var modal = document.getElementById('gcEmailModal');
  var form = document.getElementById('gcFormView');
  var success = document.getElementById('gcSuccessView');
  if (form) form.classList.remove('hidden');
  if (success) success.classList.add('hidden');
  if (modal) modal.classList.remove('hidden');
  var input = document.getElementById('gcEmailInput');
  if (input) { input.value = ''; input.focus(); }
}

function gcCloseModal() {
  var modal = document.getElementById('gcEmailModal');
  if (modal) modal.classList.add('hidden');
}

function gcOpenCoupon() {
  var url = gcPending && gcPending.url;
  gcCloseModal();
  if (url) window.open(url, '_blank', 'noopener');
}

function gcSkipEmail() {
  gcOpenCoupon();
}

function gcSubmitEmail(event) {
  event.preventDefault();
  var input = document.getElementById('gcEmailInput');
  var btn = document.getElementById('gcSubmitBtn');
  var email = (input && input.value || '').trim();
  if (!email || email.indexOf('@') === -1) return;

  var page = window.__GC_PAGE__ || {};
  var salon = gcPendingSalon || {};
  var payload = {
    email: email,
    coupon_url: gcPending && gcPending.url,
    price: (gcPending && gcPending.price) || '',
    location_name: salon.street || (page.cityLabel || ''),
    city: (page.cityLabel || '').split(',')[0],
    state: page.state || '',
    zip_code: salon.zip || ''
  };

  var original = btn ? btn.innerHTML : '';
  if (btn) { btn.innerHTML = 'Sending... ⏳'; btn.disabled = true; }

  fetch(GC_WORKER_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(function (res) {
      if (res.ok) return res.json().catch(function () { return {}; });
      return res.json().catch(function () { return {}; }).then(function (r) {
        throw new Error(r.error || 'Unable to send your coupon');
      });
    })
    .then(function () {
      var successEmail = document.getElementById('gcSuccessEmail');
      if (successEmail) successEmail.textContent = email;
      var form = document.getElementById('gcFormView');
      var success = document.getElementById('gcSuccessView');
      if (form) form.classList.add('hidden');
      if (success) success.classList.remove('hidden');
    })
    .catch(function (err) {
      alert(err.message || 'Unable to send your coupon. Please try again.');
    })
    .then(function () {
      if (btn) { btn.innerHTML = original; btn.disabled = false; }
    });
}

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') gcCloseModal();
});
