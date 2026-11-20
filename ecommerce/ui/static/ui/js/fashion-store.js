(() => {
  const products = [
    { id: 'up-001', name: 'The Essential Cotton Tee', category: 'women', price: 2163.03, image: '/static/ui/images/product-01.jpg' },
    { id: 'up-002', name: 'Relaxed Tailored Shirt', category: 'women', price: 4589.95, image: '/static/ui/images/product-04.jpg' },
    { id: 'up-003', name: 'The Weekend Knit', category: 'women', price: 3314.75, image: '/static/ui/images/product-07.jpg' },
    { id: 'up-004', name: 'Everyday Straight-Leg Jean', category: 'men', price: 9749.25, image: '/static/ui/images/product-09.jpg' },
    { id: 'up-005', name: 'The City Crossbody', category: 'accessories', price: 4527.95, image: '/static/ui/images/product-11.jpg' },
    { id: 'up-006', name: 'Linen Blend Summer Dress', category: 'women', price: 6850, image: '/static/ui/images/product-12.jpg' },
    { id: 'up-007', name: 'Classic Everyday Loafer', category: 'accessories', price: 7799, image: '/static/ui/images/product-14.jpg' },
    { id: 'up-008', name: 'The Weekend Overshirt', category: 'men', price: 5980, image: '/static/ui/images/product-16.jpg' },
    { id: 'up-009', name: 'Soft Cotton Weekend Tee', category: 'men', price: 2499, image: '/static/ui/images/product-02.jpg' },
    { id: 'up-010', name: 'The Sunday Shirt', category: 'women', price: 4290, image: '/static/ui/images/product-03.jpg' },
    { id: 'up-011', name: 'The Soft Knit Cardigan', category: 'women', price: 6490, image: '/static/ui/images/product-05.jpg' },
    { id: 'up-012', name: 'Everyday Leather Belt', category: 'accessories', price: 1990, image: '/static/ui/images/product-06.jpg' },
    { id: 'up-013', name: 'The Weekend Shirt Dress', category: 'women', price: 6990, image: '/static/ui/images/product-08.jpg' },
    { id: 'up-014', name: 'Classic Low-Top Sneaker', category: 'accessories', price: 5890, image: '/static/ui/images/product-10.jpg' },
    { id: 'up-015', name: 'Relaxed Tapered Trouser', category: 'men', price: 5190, image: '/static/ui/images/product-13.jpg' },
    { id: 'up-016', name: 'The Everyday Tote', category: 'accessories', price: 3290, image: '/static/ui/images/product-15.jpg' },
  ];
  const money = (amount) => `KSh ${Number(amount || 0).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  let cartItems = [];
  let wishlistItems = [];
  const csrfToken = () => document.cookie.split('; ').find((part) => part.startsWith('csrftoken='))?.split('=')[1] || '';
  const apiPost = async (url, payload = {}) => {
    const response = await fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(csrfToken()) },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(data.error || data.message || 'That request could not be completed.');
      error.data = data;
      throw error;
    }
    return data;
  };
  const toast = document.querySelector('[data-store-toast]');
  let toastTimer;
  const showToast = (message) => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('is-visible'), 2500);
  };
  const loadStoreState = async () => {
    try {
      const response = await fetch('/api/store-state/', { credentials: 'same-origin' });
      if (!response.ok) throw new Error('Could not load your bag.');
      const state = await response.json();
      cartItems = state.cart?.items || [];
      wishlistItems = state.wishlist || [];
      updateBadges(); renderCart(); renderCheckoutSummary(); renderWishlistPage(); updateWishlistButtons();
    } catch (error) { showToast(error.message); }
  };

  const getProductFromCard = (card) => ({
    id: card.dataset.productId,
    product_url: card.dataset.productUrl,
    slug: card.dataset.productSlug,
    name: card.dataset.name,
    category: card.dataset.category,
    price: Number(card.dataset.price),
    image: card.dataset.image || card.querySelector('img')?.src,
  });
  const renderWishlistPage = () => {
    const grid = document.querySelector('[data-wishlist-grid]');
    if (!grid) return;
    const saved = wishlistItems;
    grid.replaceChildren();
    saved.forEach((item) => {
      const card = document.createElement('article');
      card.className = 'product-card reveal is-visible';
      Object.assign(card.dataset, { productCard: '', productId: item.id, productUrl: item.product_url || '', name: item.name, category: item.category || 'women', price: item.price, image: item.image });
      const visual = document.createElement('div'); visual.className = 'product-card__visual';
      const link = document.createElement('a'); link.className = 'product-card__image-link'; link.href = item.product_url || `/product-detail/?product=${encodeURIComponent(item.slug || item.id)}`;
      const image = document.createElement('img'); image.src = item.image; image.alt = item.name; image.loading = 'lazy'; link.appendChild(image);
      const wish = document.createElement('button'); wish.className = 'product-card__wish is-active'; wish.type = 'button'; wish.setAttribute('data-wishlist-toggle', ''); wish.setAttribute('aria-label', `Remove ${item.name} from wishlist`); wish.setAttribute('aria-pressed', 'true'); wish.innerHTML = '<i class="fa fa-heart"></i>';
      const quick = document.createElement('button'); quick.className = 'product-card__quick'; quick.type = 'button'; quick.setAttribute('data-quick-open', ''); quick.textContent = 'Quick view';
      visual.append(link, wish, quick);
      const info = document.createElement('div'); info.className = 'product-card__info';
      const nameWrap = document.createElement('div'); const name = document.createElement('a'); name.className = 'product-card__name'; name.href = link.href; name.textContent = item.name;
      const category = document.createElement('span'); category.className = 'product-card__category'; category.textContent = 'Saved for later'; nameWrap.append(name, category);
      const price = document.createElement('strong'); price.className = 'product-card__price'; price.textContent = money(item.price); info.append(nameWrap, price);
      const add = document.createElement('button'); add.className = 'product-card__add'; add.type = 'button'; add.setAttribute('data-add-to-cart', ''); add.textContent = 'Add to bag';
      card.append(visual, info, add); grid.appendChild(card);
    });
    const empty = document.querySelector('[data-wishlist-empty]');
    if (empty) empty.hidden = saved.length > 0;
  };
  const updateBadges = () => {
    const cartCount = cartItems.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
    const wishlistCount = wishlistItems.length;
    document.querySelectorAll('[data-cart-count]').forEach((node) => { node.textContent = cartCount; });
    document.querySelectorAll('[data-wishlist-count]').forEach((node) => { node.textContent = wishlistCount; });
  };
  const updateWishlistButtons = () => {
    const saved = new Set(wishlistItems.map((item) => item.id));
    document.querySelectorAll('[data-product-card], [data-detail-product]').forEach((root) => {
      const productId = root.dataset.productId;
      const button = root.querySelector('[data-wishlist-toggle]');
      const active = saved.has(productId);
      button?.classList.toggle('is-active', active);
      button?.setAttribute('aria-pressed', String(active));
    });
  };
  const addToCart = async (product, quantity = 1) => {
    try {
      const result = await apiPost('/api/cart/add/', { product_id: product.id, quantity });
      cartItems = result.cart.items;
      updateBadges(); renderCart(); renderCheckoutSummary();
      showToast(`${result.product_name} added to your bag`);
    } catch (error) { showToast(error.message); }
  };

  document.addEventListener('click', (event) => {
    const addButton = event.target.closest('[data-add-to-cart]');
    if (addButton) {
      const card = addButton.closest('[data-product-card]');
      if (card) addToCart(getProductFromCard(card));
    }
    const detailAddButton = event.target.closest('[data-detail-add]');
    if (detailAddButton) {
      const detail = detailAddButton.closest('[data-detail-product]');
      const quantity = Number(document.querySelector('[data-detail-quantity]')?.value || 1);
      if (detail) addToCart({ id: detail.dataset.productId, slug: detail.dataset.productSlug, product_url: detail.dataset.productUrl, name: detail.dataset.productName, price: Number(detail.dataset.productPrice), image: detail.dataset.productImage }, quantity);
    }

    const wishlistButton = event.target.closest('[data-wishlist-toggle]');
    if (wishlistButton) {
      const card = wishlistButton.closest('[data-product-card]');
      const detail = wishlistButton.closest('[data-detail-product]');
      const product = card ? getProductFromCard(card) : detail ? {
        id: detail.dataset.productId, name: detail.dataset.productName,
        slug: detail.dataset.productSlug, product_url: detail.dataset.productUrl,
        price: Number(detail.dataset.productPrice), image: detail.dataset.productImage,
      } : null;
      if (product) apiPost('/api/wishlist/toggle/', { product_id: product.id }).then((result) => {
        wishlistItems = result.wishlist;
        updateBadges(); updateWishlistButtons();
        if (document.querySelector('[data-wishlist-page]')) renderWishlistPage();
        showToast(result.saved ? 'Saved to your wishlist' : 'Removed from your wishlist');
      }).catch((error) => showToast(error.message));
    }

    const quickOpen = event.target.closest('[data-quick-open]');
    if (quickOpen) openQuickView(getProductFromCard(quickOpen.closest('[data-product-card]')));
    if (event.target.closest('[data-quick-close]')) closeQuickView();

    const qtyButton = event.target.closest('[data-qty-minus], [data-qty-plus]');
    if (qtyButton) {
      const field = document.querySelector('[data-detail-quantity]');
      if (field) field.value = Math.max(1, Math.min(10, Number(field.value || 1) + (qtyButton.hasAttribute('data-qty-plus') ? 1 : -1)));
    }

    const thumb = event.target.closest('[data-gallery-thumb]');
    if (thumb) {
      document.querySelectorAll('[data-gallery-thumb]').forEach((item) => item.classList.toggle('is-active', item === thumb));
      const mainImage = document.querySelector('[data-gallery-main]');
      if (mainImage) mainImage.src = thumb.dataset.galleryThumb;
    }

    const sizeButton = event.target.closest('.size-button');
    if (sizeButton) {
      document.querySelectorAll('.size-button').forEach((item) => item.classList.toggle('is-selected', item === sizeButton));
    }
    const swatch = event.target.closest('.swatch');
    if (swatch) {
      document.querySelectorAll('.swatch').forEach((item) => item.classList.toggle('is-selected', item === swatch));
    }

    const tab = event.target.closest('[data-tab]');
    if (tab) {
      document.querySelectorAll('[data-tab]').forEach((item) => item.classList.toggle('is-active', item === tab));
      document.querySelectorAll('[data-tab-panel]').forEach((panel) => { panel.hidden = panel.dataset.tabPanel !== tab.dataset.tab; });
    }

    const removeButton = event.target.closest('[data-cart-remove]');
    if (removeButton) {
      apiPost('/api/cart/remove/', { product_id: removeButton.dataset.cartRemove }).then((result) => {
        cartItems = result.cart.items; renderCart(); renderCheckoutSummary(); updateBadges();
      }).catch((error) => showToast(error.message));
    }
    if (event.target.closest('[data-clear-cart]')) {
      apiPost('/api/cart/clear/').then((result) => {
        cartItems = result.cart.items; renderCart(); renderCheckoutSummary(); updateBadges();
      }).catch((error) => showToast(error.message));
    }

    const accountToggle = event.target.closest('[data-account-toggle]');
    if (accountToggle) {
      const dropdown = accountToggle.closest('.store-header__dropdown');
      const isOpen = dropdown.classList.contains('is-open');
      document.querySelectorAll('.store-header__dropdown.is-open').forEach((d) => { d.classList.remove('is-open'); });
      dropdown.classList.toggle('is-open', !isOpen);
      accountToggle.setAttribute('aria-expanded', String(!isOpen));
    }
    const mobileMenu = event.target.closest('[data-menu-toggle]');
    if (mobileMenu) {
      const nav = document.querySelector('.store-header__nav');
      const open = mobileMenu.getAttribute('aria-expanded') !== 'true';
      mobileMenu.setAttribute('aria-expanded', String(open));
      nav?.classList.toggle('is-open', open);
    }
    const dropdown = event.target.closest('.store-header__dropdown > a');
    if (dropdown && window.matchMedia('(max-width: 760px)').matches) {
      event.preventDefault();
      dropdown.parentElement.classList.toggle('is-open');
    }
    if (event.target.closest('[data-track-order]')) {
      event.preventDefault();
      showToast('Order tracking will be available when store services are connected.');
    }

    const heroDot = event.target.closest('[data-hero-dot]');
    if (heroDot) showHero(Number(heroDot.dataset.heroDot));
    if (event.target.closest('[data-hero-next]')) showHero(heroIndex + 1);
    if (event.target.closest('[data-hero-prev]')) showHero(heroIndex - 1);
  });

  const quickView = document.querySelector('[data-quick-view]');
  let quickProduct = null;
  const openQuickView = (product) => {
    if (!quickView || !product) return;
    quickProduct = product;
    quickView.querySelector('[data-quick-image]').src = product.image;
    quickView.querySelector('[data-quick-image]').alt = product.name;
    quickView.querySelector('[data-quick-title]').textContent = product.name;
    quickView.querySelector('[data-quick-price]').textContent = money(product.price);
    quickView.querySelector('[data-quick-link]').href = product.product_url || `/product-detail/?product=${encodeURIComponent(product.slug || product.id)}`;
    quickView.hidden = false;
    document.body.classList.add('dialog-open');
  };
  const closeQuickView = () => {
    if (quickView) quickView.hidden = true;
    document.body.classList.remove('dialog-open');
  };
  quickView?.querySelector('[data-quick-view-add]')?.addEventListener('click', () => quickProduct && addToCart(quickProduct));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeQuickView(); });

  const renderCart = () => {
    const lines = document.querySelector('[data-cart-lines]');
    if (!lines) return;
    const cart = cartItems;
    const wrap = document.querySelector('[data-cart-items-wrap]');
    const empty = document.querySelector('[data-cart-empty]');
    if (wrap) wrap.hidden = cart.length === 0;
    if (empty) empty.hidden = cart.length > 0;
    lines.replaceChildren();
    cart.forEach((item) => {
      const row = document.createElement('tr');
      const productCell = document.createElement('td'); productCell.colSpan = 2;
      const productWrap = document.createElement('div'); productWrap.className = 'cart-product';
      const image = document.createElement('img'); image.src = item.image; image.alt = '';
      const description = document.createElement('div'); const name = document.createElement('strong'); name.textContent = item.name;
      const subtitle = document.createElement('span'); subtitle.textContent = 'Everyday edit'; description.append(name, subtitle); productWrap.append(image, description); productCell.appendChild(productWrap);
      const unitPrice = document.createElement('td'); unitPrice.textContent = money(item.price);
      const quantityCell = document.createElement('td'); const quantityWrap = document.createElement('div'); quantityWrap.className = 'cart-quantity';
      const decrease = document.createElement('button'); decrease.type = 'button'; decrease.dataset.cartQty = '-1'; decrease.dataset.cartId = item.id; decrease.setAttribute('aria-label', 'Decrease quantity'); decrease.textContent = '−';
      const quantityInput = document.createElement('input'); quantityInput.value = item.quantity; quantityInput.readOnly = true; quantityInput.setAttribute('aria-label', 'Quantity');
      const increase = document.createElement('button'); increase.type = 'button'; increase.dataset.cartQty = '1'; increase.dataset.cartId = item.id; increase.setAttribute('aria-label', 'Increase quantity'); increase.textContent = '+';
      quantityWrap.append(decrease, quantityInput, increase); quantityCell.appendChild(quantityWrap);
      const totalCell = document.createElement('td'); totalCell.textContent = money(item.price * item.quantity);
      const removeCell = document.createElement('td'); const remove = document.createElement('button'); remove.className = 'cart-remove'; remove.type = 'button'; remove.dataset.cartRemove = item.id; remove.setAttribute('aria-label', `Remove ${item.name}`); remove.textContent = '×'; removeCell.appendChild(remove);
      row.append(productCell, unitPrice, quantityCell, totalCell, removeCell);
      lines.appendChild(row);
    });
    const subtotal = cart.reduce((sum, item) => sum + Number(item.price) * Number(item.quantity), 0);
    const shipping = subtotal === 0 || subtotal >= 6499.5 ? 0 : 350;
    const setText = (selector, value) => document.querySelectorAll(selector).forEach((node) => { node.textContent = value; });
    setText('[data-cart-subtotal]', money(subtotal));
    setText('[data-cart-shipping]', shipping ? money(shipping) : 'Free');
    setText('[data-cart-total]', money(subtotal + shipping));
    document.querySelectorAll('[data-checkout-link]').forEach((link) => { link.classList.toggle('is-disabled', !cart.length); });
  };

  document.addEventListener('click', (event) => {
    const quantity = event.target.closest('[data-cart-qty]');
    if (!quantity) return;
    const item = cartItems.find((product) => product.id === quantity.dataset.cartId);
    if (!item) return;
    const nextQuantity = Math.max(1, Math.min(Number(item.stock_quantity || 10), Number(item.quantity) + Number(quantity.dataset.cartQty)));
    apiPost('/api/cart/update/', { product_id: item.id, quantity: nextQuantity }).then((result) => {
      cartItems = result.cart.items; renderCart(); renderCheckoutSummary(); updateBadges();
    }).catch((error) => showToast(error.message));
  });

  const renderCheckoutSummary = () => {
    const checkoutLines = document.querySelector('[data-checkout-lines]');
    if (!checkoutLines) return;
    const cart = cartItems;
    checkoutLines.replaceChildren();
    checkoutLines.classList.add('checkout-lines');
    cart.forEach((item) => {
      const line = document.createElement('div');
      line.className = 'checkout-line';
      line.innerHTML = '<span></span><strong></strong>';
      line.children[0].textContent = `${item.name} × ${item.quantity}`;
      line.children[1].textContent = money(item.price * item.quantity);
      checkoutLines.appendChild(line);
    });
    const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const shipping = subtotal === 0 || subtotal >= 6499.5 ? 0 : 350;
    document.querySelector('[data-checkout-subtotal]').textContent = money(subtotal);
    document.querySelector('[data-checkout-shipping]').textContent = shipping ? money(shipping) : 'Free';
    document.querySelector('[data-checkout-total]').textContent = money(subtotal + shipping);
  };
  let checkoutStep = 1;
  let pendingMpesaOrder = null;
  const setCheckoutMessage = (title, message) => {
    document.querySelector('[data-checkout-success-title]').textContent = title;
    document.querySelector('[data-checkout-success-message]').textContent = message;
    document.querySelector('[data-checkout-success]').hidden = false;
  };
  const pollMpesaStatus = async (reference, attempt = 0) => {
    try {
      const response = await fetch(`/payments/status/${encodeURIComponent(reference)}/`, { credentials: 'same-origin' });
      const state = await response.json();
      if (!response.ok) throw new Error(state.error || 'Could not check payment status.');
      if (state.status === 'succeeded') {
        const receipt = state.receipt_number ? ` M-Pesa receipt: ${state.receipt_number}.` : '';
        setCheckoutMessage('Payment confirmed.', `Order ${pendingMpesaOrder.slice(0, 8)} is confirmed.${receipt}`);
        return;
      }
      if (state.status === 'failed' || state.status === 'cancelled') {
        setCheckoutMessage('The M-Pesa payment did not complete.', 'Your order is still pending. You can request another payment prompt.');
        document.querySelector('[data-retry-mpesa]').hidden = false;
        return;
      }
      if (attempt >= 40) {
        setCheckoutMessage('Waiting for M-Pesa confirmation.', 'Your order remains pending. It will update when Safaricom confirms payment.');
        return;
      }
      window.setTimeout(() => pollMpesaStatus(reference, attempt + 1), 3000);
    } catch (error) {
      setCheckoutMessage('Payment status is not available yet.', error.message);
    }
  };
  const startMpesaPayment = async (orderNumber) => {
    const retryButton = document.querySelector('[data-retry-mpesa]');
    retryButton.hidden = true;
    setCheckoutMessage('Starting M-Pesa payment…', 'Please wait while we contact Safaricom.');
    try {
      const result = await apiPost('/payments/stk-push/', { order_number: orderNumber });
      setCheckoutMessage('Check your phone.', result.message);
      pollMpesaStatus(result.reference);
    } catch (error) {
      const paymentStatus = error.data?.payment?.status;
      setCheckoutMessage('Your order is saved, but the M-Pesa prompt did not start.', error.message);
      retryButton.hidden = paymentStatus !== 'failed';
    }
  };
  const showCheckoutStep = (step) => {
    checkoutStep = step;
    document.querySelectorAll('[data-checkout-panel]').forEach((panel) => { panel.hidden = Number(panel.dataset.checkoutPanel) !== step; });
    document.querySelectorAll('[data-checkout-indicator]').forEach((indicator) => indicator.classList.toggle('is-active', Number(indicator.dataset.checkoutIndicator) === step));
    if (step === 3) {
      const value = (selector) => document.querySelector(selector)?.value || '';
      document.querySelector('[data-checkout-review-address]').textContent = `${value('#checkout-first')} ${value('#checkout-last')}, ${value('#checkout-address')}, ${value('#checkout-city')}, ${value('#checkout-county')}`;
      document.querySelector('[data-checkout-review-contact]').textContent = `${value('#checkout-email')} · ${value('#checkout-phone')}`;
      document.querySelector('[data-checkout-review-payment]').textContent = document.querySelector('[name="payment"]:checked')?.value === 'mpesa' ? 'M-Pesa' : 'Pay on delivery';
    }
  };
  document.addEventListener('click', (event) => {
    const next = event.target.closest('[data-checkout-next]');
    const back = event.target.closest('[data-checkout-back]');
    if (next) {
      if (!cartItems.length) { showToast('Your bag is empty. Add a piece before checkout.'); return; }
      if (checkoutStep === 1 && !document.querySelector('[data-checkout-form]').reportValidity()) return;
      showCheckoutStep(Math.min(3, checkoutStep + 1));
    }
    if (back) showCheckoutStep(Math.max(1, checkoutStep - 1));
  });
  document.querySelector('[data-retry-mpesa]')?.addEventListener('click', () => {
    if (pendingMpesaOrder) startMpesaPayment(pendingMpesaOrder);
  });
  document.querySelector('[data-checkout-form]')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (checkoutStep !== 3) return;
    if (!cartItems.length) {
      showToast('Your bag is empty. Add a piece before checkout.');
      return;
    }
    const value = (selector) => document.querySelector(selector)?.value.trim() || '';
    const paymentMethod = document.querySelector('[name="payment"]:checked')?.value || 'pay_on_delivery';
    const submitButton = event.currentTarget.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    try {
      const result = await apiPost('/api/checkout/', {
        first_name: value('#checkout-first'), last_name: value('#checkout-last'),
        email: value('#checkout-email'), phone: value('#checkout-phone'),
        address: value('#checkout-address'), city: value('#checkout-city'),
        county: value('#checkout-county'),
        payment_method: paymentMethod,
      });
      pendingMpesaOrder = result.order_number;
      cartItems = [];
      renderCart(); renderCheckoutSummary(); updateBadges();
      document.querySelector('[data-checkout-success] h2').textContent = `Thank you — order ${result.order_number.slice(0, 8)} is recorded.`;
      document.querySelector('[data-checkout-success] p').textContent = `Your order is pending. Total: ${money(result.total)}. Payment has not been collected.`;
      document.querySelector('[data-checkout-success]').hidden = false;
      const trackLink = document.querySelector('[data-track-link]');
      if (trackLink) trackLink.href = `/track-order/?order_number=${encodeURIComponent(result.order_number)}`;
      if (paymentMethod === 'mpesa') {
        await startMpesaPayment(result.order_number);
      } else {
        setCheckoutMessage(`Thank you - order ${result.order_number.slice(0, 8)} is recorded.`, `Your order is pending. Total: ${money(result.total)}. Payment is due on delivery.`);
      }
      submitButton.hidden = true;
    } catch (error) {
      showToast(error.message);
      submitButton.disabled = false;
    }
  });

  const productGrid = document.querySelector('[data-product-search-grid]');
  if (productGrid) {
    const cards = [...productGrid.querySelectorAll('[data-product-card]')];
    let activeCategory = 'all';
    let searchTerm = new URLSearchParams(window.location.search).get('q')?.trim().toLowerCase() || '';
    const categoryParam = new URLSearchParams(window.location.search).get('category');
    if (categoryParam) activeCategory = categoryParam;
    const priceRange = document.querySelector('[data-price-filter]');
    const categoryChecks = [...document.querySelectorAll('[data-category-filter]')];
    const badgeChecks = [...document.querySelectorAll('[data-badge-filter]')];
    const sortSelect = document.querySelector('[data-product-sort]');
    const filterCards = () => {
      const selected = categoryChecks.filter((input) => input.checked).map((input) => input.dataset.categoryFilter);
      const categories = selected.length ? selected : activeCategory === 'all' ? [] : [activeCategory];
      const selectedBadges = badgeChecks.filter((input) => input.checked).map((input) => input.dataset.badgeFilter.toLowerCase());
      let count = 0;
      cards.forEach((card) => {
        const categoryOk = !categories.length || categories.includes(card.dataset.category);
        const searchOk = !searchTerm || card.dataset.name.toLowerCase().includes(searchTerm);
        const priceOk = !priceRange || Number(card.dataset.price) <= Number(priceRange.value);
        const badgeOk = !selectedBadges.length || selectedBadges.includes((card.dataset.badge || '').toLowerCase());
        const visible = categoryOk && searchOk && priceOk && badgeOk;
        card.hidden = !visible;
        if (visible) count += 1;
      });
      const countNode = document.querySelector('[data-product-count]');
      if (countNode) countNode.textContent = `${count} ${count === 1 ? 'piece' : 'pieces'}`;
      const empty = document.querySelector('[data-empty-filter]');
      if (empty) empty.hidden = count > 0;
      document.querySelectorAll('[data-category-chip]').forEach((chip) => chip.classList.toggle('is-active', chip.dataset.categoryChip === (categories[0] || 'all')));
    };
    document.querySelectorAll('[data-category-chip]').forEach((chip) => chip.addEventListener('click', () => {
      activeCategory = chip.dataset.categoryChip;
      categoryChecks.forEach((check) => { check.checked = false; });
      filterCards();
    }));
    categoryChecks.forEach((check) => check.addEventListener('change', filterCards));
    badgeChecks.forEach((check) => check.addEventListener('change', filterCards));
    priceRange?.addEventListener('input', () => {
      const label = document.querySelector('[data-price-maximum]');
      if (label) label.textContent = money(priceRange.value);
      filterCards();
    });
    sortSelect?.addEventListener('change', () => {
      const sorted = [...cards];
      if (sortSelect.value === 'price-low') sorted.sort((a, b) => Number(a.dataset.price) - Number(b.dataset.price));
      if (sortSelect.value === 'price-high') sorted.sort((a, b) => Number(b.dataset.price) - Number(a.dataset.price));
      if (sortSelect.value === 'name') sorted.sort((a, b) => a.dataset.name.localeCompare(b.dataset.name));
      sorted.forEach((card) => productGrid.appendChild(card));
    });
    if (searchTerm && document.querySelector('#store-search')) document.querySelector('#store-search').value = searchTerm;
    filterCards();
  }

  const searchForm = document.querySelector('[data-search-form]');
  const searchInput = searchForm?.querySelector('input[type="search"]');
  const suggestions = searchForm?.querySelector('[data-search-suggestions]');
  if (searchInput && suggestions) {
    const productUrl = searchForm.action;
    const showSuggestions = () => {
      const query = searchInput.value.trim().toLowerCase();
      suggestions.replaceChildren();
      if (!query) { suggestions.hidden = true; return; }
      const matches = products.filter((item) => item.name.toLowerCase().includes(query)).slice(0, 5);
      if (!matches.length) { suggestions.hidden = true; return; }
      matches.forEach((item) => {
        const link = document.createElement('a');
        link.href = `${productUrl}?q=${encodeURIComponent(item.name)}`;
        const image = document.createElement('img'); image.src = item.image; image.alt = '';
        const label = document.createElement('span'); label.textContent = item.name;
        const price = document.createElement('strong'); price.textContent = money(item.price);
        link.append(image, label, price); suggestions.appendChild(link);
      });
      suggestions.hidden = false;
    };
    searchInput.addEventListener('input', showSuggestions);
    searchInput.addEventListener('focus', showSuggestions);
    document.addEventListener('click', (event) => { if (!searchForm.contains(event.target)) suggestions.hidden = true; });
    document.addEventListener('click', (event) => {
      const accountWrap = event.target.closest('.store-header__dropdown');
      const hasTrigger = accountWrap && (accountWrap.querySelector('[data-account-toggle]') || accountWrap.querySelector('[data-megamenu-toggle]'));
      if (!accountWrap || !hasTrigger) {
        document.querySelectorAll('.store-header__dropdown.is-open').forEach((d) => { d.classList.remove('is-open'); });
        document.querySelectorAll('[data-account-toggle]').forEach((b) => b.setAttribute('aria-expanded', 'false'));
      }
    });
    searchForm.addEventListener('submit', (event) => {
      event.preventDefault();
      const query = searchInput.value.trim();
      window.location.href = `${productUrl}?q=${encodeURIComponent(query)}`;
    });
  }

  let heroIndex = 0;
  const heroSlides = [...document.querySelectorAll('[data-hero-slide]')];
  const showHero = (index) => {
    if (!heroSlides.length) return;
    heroIndex = (index + heroSlides.length) % heroSlides.length;
    heroSlides.forEach((slide, i) => slide.classList.toggle('is-active', i === heroIndex));
    document.querySelectorAll('[data-hero-dot]').forEach((dot, i) => dot.classList.toggle('is-active', i === heroIndex));
  };
  if (heroSlides.length > 1) setInterval(() => showHero(heroIndex + 1), 5500);

  document.querySelector('[data-newsletter-form]')?.addEventListener('submit', (event) => {
    event.preventDefault(); event.currentTarget.reset(); showToast('Thanks for joining the Upsteps note.');
  });
  document.querySelector('[data-contact-form]')?.addEventListener('submit', (event) => {
    event.preventDefault(); document.querySelector('[data-contact-success]').hidden = false; event.currentTarget.reset();
  });

  loadStoreState();
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
    }), { threshold: 0.12 });
    document.querySelectorAll('.reveal').forEach((node) => observer.observe(node));
  } else document.querySelectorAll('.reveal').forEach((node) => node.classList.add('is-visible'));
})();
