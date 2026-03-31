const API_URL = 'http://localhost:5000/api';
let configState = null;
let previousPrices = {};
const STATIC_DELTA_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "PAXGUSDT", "SOLUSDT", "RIVERUSDT", "XRPUSDT", "SLVONUSDT", 
    "PIPPINUSDT", "LIGHTUSDT", "DOGEUSDT", "DUSKUSDT", "LINKUSDT", "BNBUSDT", "BEATUSDT",
    "ZECUSDT", "LTCUSDT", "AINUSDT", "BCHUSDT", "PARTIUSDT", "AVAXUSDT", "DOTUSDT", 
    "FRAXUSDT", "KITEUSDT", "VVVUSDT", "AVAAIUSDT", "JTOUSDT", "AAVEUSDT", "MUSDT", 
    "HUSDT", "SIGNUSDT", "TAOUSDT", "HYPEUSDT", "KAITOUSDT", "BLESSUSDT", "TSLAXUSDT", 
    "FARTCOINUSDT", "UNIUSDT", "VIRTUALUSDT", "NVDAXUSDT", "POLUSDT", "TSTUSDT", 
    "ADAUSDT", "IPUSDT", "PIUSDT"
];

let userSubscription = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    
    // Bind the Test Alert Button
    document.getElementById('test-alert-btn').addEventListener('click', async (e) => {
        const btn = e.target;
        btn.innerText = "Sending...";
        try {
            const res = await fetch(`${API_URL}/test_alert`, { method: 'POST' });
            const data = await res.json();
            if(data.success) {
                btn.innerText = "Sent Successfully!";
                btn.style.color = "var(--accent-success)";
                btn.style.borderColor = "var(--accent-success)";
            } else {
                btn.innerText = "Failed";
                btn.style.color = "red";
            }
        } catch(err) {
            btn.innerText = "Network Error";
        }
        setTimeout(() => {
            btn.innerText = "Send Test Alert";
            btn.style.color = ""; btn.style.borderColor = "";
        }, 3000);
    });
});

async function initApp() {
    try {
        const configRes = await fetch(`${API_URL}/config`);
        configState = await configRes.json();
        
        await fetchUserSubscription();
        
        renderCompleteUI();
        bindMainToggles();
        
        // Start Live Intelligence Polling
        setInterval(updateActiveIntelligence, 1000);
        updateActiveIntelligence();
    } catch(e) {
        console.error("Failed to fetch initial configuration from backend", e);
    }
}

async function fetchUserSubscription() {
    try {
        const res = await fetch(`${API_URL}/user/subscription`);
        userSubscription = await res.json();
        updateUsageUI();
    } catch(e) {
        console.error("Subscription fetch failed", e);
    }
}

function updateUsageUI() {
    if (!userSubscription) return;
    
    document.getElementById('usage-banner').classList.remove('hidden');
    
    const { usage, limits, tier } = userSubscription;
    
    const alertsText = `${usage.alerts}/${limits.max_alerts === Infinity ? '∞' : limits.max_alerts}`;
    document.getElementById('usage-alerts').innerText = alertsText;
    const alertPercent = limits.max_alerts === Infinity ? 0 : (usage.alerts / limits.max_alerts) * 100;
    document.getElementById('progress-alerts').style.width = `${Math.min(alertPercent, 100)}%`;
    
    const indText = `${usage.indicators}/${limits.max_indicators === Infinity ? '∞' : limits.max_indicators}`;
    document.getElementById('usage-indicators').innerText = indText;
    const indPercent = limits.max_indicators === Infinity ? 0 : (usage.indicators / limits.max_indicators) * 100;
    document.getElementById('progress-indicators').style.width = `${Math.min(indPercent, 100)}%`;
}

function showPricing() {
    document.getElementById('main-dashboard').classList.add('hidden');
    const modal = document.getElementById('pricingModal');
    modal.style.display = 'flex';
    modal.classList.add('pricing-mode');
    const bgVideo = document.getElementById('pricing-bg-video');
    if (bgVideo) { bgVideo.style.display = 'block'; bgVideo.play(); }
}

function closePricingModal() {
    const modal = document.getElementById('pricingModal');
    modal.style.display = 'none';
    modal.classList.remove('pricing-mode');
    document.getElementById('main-dashboard').classList.remove('hidden');
    setActiveNav('Dashboard');
    const bgVideo = document.getElementById('pricing-bg-video');
    if (bgVideo) { bgVideo.style.display = 'none'; bgVideo.pause(); }
}

function setActiveNav(name) {
    document.querySelectorAll('.nav-item').forEach(item => {
        if(item.innerText === name) item.classList.add('active');
        else item.classList.remove('active');
    });
}

function showDashboard() {
    closePricingModal();
    document.getElementById('live-intelligence-view').classList.add('hidden');
    document.getElementById('profile-view').classList.add('hidden');
    document.getElementById('main-dashboard').classList.remove('hidden');
    setActiveNav('Dashboard');
}

function showLiveIntelligence() {
    closePricingModal();
    document.getElementById('main-dashboard').classList.add('hidden');
    document.getElementById('profile-view').classList.add('hidden');
    document.getElementById('live-intelligence-view').classList.remove('hidden');
    setActiveNav('Live Intelligence');
}

function showProfile() {
    closePricingModal();
    document.getElementById('main-dashboard').classList.add('hidden');
    document.getElementById('live-intelligence-view').classList.add('hidden');
    document.getElementById('profile-view').classList.remove('hidden');
    setActiveNav('Account');
    loadProfileData();
}

function showBacktesting() {
    showToast("Backtesting engine initializing...");
    setActiveNav('Backtesting');
}

function showCommunity() {
    showToast("Opening TradePulse Social...");
    setActiveNav('Community');
}

function showContact() {
    showToast("Contact support: support@tradepulse.io");
    setActiveNav('Contact');
}

async function handleSubscription(tier) {
    const isAnnual = document.getElementById('billing-cycle-toggle').checked;
    try {
        const orderRes = await fetch(`${API_URL}/create-order`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ tier, isAnnual })
        });
        const order = await orderRes.json();
        
        const options = {
            "key": "rzp_test_replace_me",
            "amount": order.amount,
            "currency": "INR",
            "name": "TradePulse Algo",
            "description": `${tier} Plan ${isAnnual ? 'Annual' : 'Monthly'} Subscription`,
            "order_id": order.id,
            "handler": async function (response) {
                const verifyRes = await fetch(`${API_URL}/verify-payment`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ...response, tier })
                });
                const result = await verifyRes.json();
                if(result.status === 'success') {
                    showToast(`Successfully upgraded to ${tier}!`);
                    await fetchUserSubscription();
                    closePricingModal();
                } else {
                    alert("Payment verification failed.");
                }
            },
            "theme": { "color": "#3b82f6" }
        };
        const rzp = new Razorpay(options);
        rzp.open();
    } catch(e) {
        console.error("Order creation failed", e);
        showToast("Error creating payment order. Try again.");
    }
}

function toggleBillingCycle() {
    const isAnnual = document.getElementById('billing-cycle-toggle').checked;
    const prices = {
        'STARTER': isAnnual ? '₹1490' : '₹149',
        'PRO': isAnnual ? '₹3990' : '₹399',
        'ELITE': isAnnual ? '₹7990' : '₹799'
    };
    
    // Update UI prices
    document.querySelector('.pricing-card.popular .card-price').innerHTML = `${prices.STARTER}<span>/${isAnnual ? 'yr' : 'mo'}</span>`;
    document.querySelectorAll('.pricing-card')[2].querySelector('.card-price').innerHTML = `${prices.PRO}<span>/${isAnnual ? 'yr' : 'mo'}</span>`;
    document.querySelectorAll('.pricing-card')[3].querySelector('.card-price').innerHTML = `${prices.ELITE}<span>/${isAnnual ? 'yr' : 'mo'}</span>`;
    
    showToast(isAnnual ? "Annual billing selected - 17% discount applied!" : "Monthly billing selected");
}

async function saveConfigToBackend() {
    try {
        await fetch(`${API_URL}/config`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(configState)
        });
    } catch(e) {
        console.error("Failed to save configuration", e);
    }
}

function bindMainToggles() {
    const indianToggle = document.getElementById('toggle-indian');
    const cryptoToggle = document.getElementById('toggle-crypto');
    
    indianToggle.checked = configState.indian_enabled;
    cryptoToggle.checked = configState.crypto_enabled;
    
    // Setup classes
    if(indianToggle.checked) indianToggle.closest('.market-card').classList.add('active');
    if(cryptoToggle.checked) cryptoToggle.closest('.market-card').classList.add('active');

    indianToggle.addEventListener('change', (e) => {
        configState.indian_enabled = e.target.checked;
        const card = e.target.closest('.market-card');
        e.target.checked ? card.classList.add('active') : card.classList.remove('active');
        playHapticSound();
        saveConfigToBackend();
    });

    cryptoToggle.addEventListener('change', (e) => {
        configState.crypto_enabled = e.target.checked;
        const card = e.target.closest('.market-card');
        e.target.checked ? card.classList.add('active') : card.classList.remove('active');
        playHapticSound();
        saveConfigToBackend();
    });
}

function renderCompleteUI() {
    renderGrid('indian', configState.indian_indicators);
    renderGrid('crypto', configState.crypto_indicators);
}

function renderGrid(market, indicators) {
    const grid = document.getElementById(`${market}-grid`);
    grid.innerHTML = ''; // Clear existing
    
    indicators.forEach((ind, index) => {
        const div = document.createElement('div');
        div.className = `indicator-item ${ind.active ? 'active' : ''}`;
        
        // Setup display details
        let dotColorClass = ind.type === 'supertrend' ? 'supertrend-dot' : 'ema-dot';
        
        let displayName = "";
        if(ind.type === 'supertrend') displayName = `Supertrend (${ind.period}, ${ind.multiplier})`;
        else if(ind.type === 'ema') displayName = `EMA (${ind.length})`;
        else if(ind.type === 'ema_cross') displayName = `EMA Cross (${ind.short}/${ind.long})`;
        else if(ind.type === 'vwap') displayName = `VWAP (${ind.source}, ${ind.anchor})`;
        else if(ind.type === 'atr') displayName = `ATR (${ind.length})`;
        else if(ind.type === 'bb') displayName = `BB (${ind.length}, ${ind.mult})`;

        let targetSymbol = ind.symbol ? `<span style="background:rgba(255,255,255,0.1);padding:2px 6px;border-radius:4px;font-size:0.75rem;margin-right:8px;font-weight:600;">${ind.symbol}</span>` : '';

        div.innerHTML = `
            <div>
                <div class="indicator-title">
                    <div class="dot ${dotColorClass}"></div>
                    <span>${targetSymbol}${displayName}</span>
                </div>
                <!-- Delete Button -->
                <small style="color:var(--text-secondary); cursor:pointer; font-size:0.75rem; margin-top:8px; display:inline-block; transition:0.2s" onmouseover="this.style.color='red'" onmouseout="this.style.color='var(--text-secondary)'" onclick="deleteIndicator('${market}', ${index})">Remove Strategy</small>
            </div>
            <label class="toggle-switch small">
                <input type="checkbox" class="sub-toggle" onchange="toggleIndicatorStatus('${market}', ${index}, this.checked)" ${ind.active ? 'checked' : ''}>
                <span class="slider"></span>
            </label>
        `;
        grid.appendChild(div);
    });
}

function toggleIndicatorStatus(market, index, isActive) {
    const key = market === 'indian' ? 'indian_indicators' : 'crypto_indicators';
    configState[key][index].active = isActive;
    // Rerender specific grid to update class active states
    renderGrid(market, configState[key]);
    saveConfigToBackend();
    updateBackendUsage();
}

async function updateBackendUsage() {
    // This is a helper to update the backend with the latest counts
    const indianInd = configState.indian_indicators.length;
    const cryptoInd = configState.crypto_indicators.length;
    
    await fetch(`${API_URL}/user/update-usage`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ indicators: indianInd + cryptoInd })
    });
    fetchUserSubscription();
}

function deleteIndicator(market, index) {
    const key = market === 'indian' ? 'indian_indicators' : 'crypto_indicators';
    configState[key].splice(index, 1);
    renderGrid(market, configState[key]);
    saveConfigToBackend();
    updateBackendUsage();
}

// Modal Logic
let deltaSymbolsCache = null;

async function openIndicatorModal(marketContext) {
    document.getElementById('algoModal').style.display = 'flex';
    document.getElementById('current-market-context').value = marketContext;
    
    // Render dynamic asset selector
    const container = document.getElementById('asset-selector-container');
    if (marketContext === 'crypto') {
        container.innerHTML = `<select id="algo-symbol">
            ${STATIC_DELTA_SYMBOLS.sort().map(s => `<option value="${s}">${s}</option>`).join('')}
        </select>`;
    } else {
        container.innerHTML = `<input type="text" id="algo-symbol" placeholder="e.g. TCS (Indian Market)" value="TCS">`;
    }

    renderAlgoParams(); // initialize params forms
    
    // Check limits
    const { usage, limits } = userSubscription;
    if (usage.indicators >= limits.max_indicators) {
        const modalBody = document.querySelector('#algoModal .modal-body');
        const originalContent = modalBody.innerHTML;
        modalBody.innerHTML = `
            <div class="locked-feature" style="padding: 2rem 0; text-align: center;">
                <div class="lock-overlay">
                    <div class="lock-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                    </div>
                    <div class="lock-message">Strategy Limit Reached</div>
                    <button class="primary-btn" onclick="showPricing(); closeIndicatorModal();" style="width: auto; padding: 0.5rem 1.5rem;">Upgrade to Unlock</button>
                </div>
                <div style="opacity: 0.3">${originalContent}</div>
            </div>
        `;
    }
}

function closeIndicatorModal() {
    document.getElementById('algoModal').style.display = 'none';
}

function renderAlgoParams() {
    const type = document.getElementById('algo-type-select').value;
    const container = document.getElementById('dynamic-params-container');
    
    if(type === 'supertrend') {
        container.innerHTML = `
            <div class="form-group">
                <label>Period</label>
                <input type="number" id="param-period" value="31">
            </div>
            <div class="form-group">
                <label>Multiplier</label>
                <input type="number" step="0.1" id="param-mult" value="2.0">
            </div>
        `;
    } else if(type === 'ema') {
        container.innerHTML = `
            <div class="form-group">
                <label>Length</label>
                <input type="number" id="param-length" value="15">
            </div>
        `;
    } else if(type === 'ema_cross') {
        container.innerHTML = `
            <div class="form-group">
                <label>Short (EMA)</label>
                <input type="number" id="param-short" value="9">
            </div>
            <div class="form-group">
                <label>Long (EMA)</label>
                <input type="number" id="param-long" value="15">
            </div>
        `;
    } else if(type === 'vwap') {
        container.innerHTML = `
            <div class="form-group">
                <label>Source</label>
                <select id="param-source">
                    <option value="hlc3">hlc3 (High-Low-Close/3)</option>
                    <option value="close">Close</option>
                    <option value="open">Open</option>
                </select>
            </div>
            <div class="form-group">
                <label>Anchor Period</label>
                <select id="param-anchor">
                    <option value="session">Session (Day)</option>
                    <option value="week">Week</option>
                    <option value="month">Month</option>
                </select>
            </div>
        `;
    } else if(type === 'atr') {
        container.innerHTML = `
            <div class="form-group">
                <label>ATR Length</label>
                <input type="number" id="param-length" value="14">
            </div>
        `;
    } else if(type === 'bb') {
        container.innerHTML = `
            <div class="form-group">
                <label>BB Length</label>
                <input type="number" id="param-length" value="20">
            </div>
            <div class="form-group">
                <label>BB Mult</label>
                <input type="number" step="0.1" id="param-mult" value="2.0">
            </div>
            <div class="form-group">
                <label>BB Offset</label>
                <input type="number" id="param-offset" value="0">
            </div>
        `;
    }
    
    // Always append Timeframe selection for all algo types
    container.innerHTML += `
        <div class="form-group">
            <label>Timeframe (Minutes)</label>
            <select id="param-timeframe">
                <option value="1">1 Minute</option>
                <option value="5">5 Minutes</option>
                <option value="10" selected>10 Minutes</option>
                <option value="15">15 Minutes</option>
                <option value="30">30 Minutes</option>
                <option value="60">1 Hour</option>
            </select>
        </div>
    `;
}

function saveNewAlgorithm() {
    const market = document.getElementById('current-market-context').value;
    const type = document.getElementById('algo-type-select').value;
    let symbolEl = document.getElementById('algo-symbol');
    let targetSymbol = symbolEl ? symbolEl.value.trim().toUpperCase() : '';
    
    const key = market === 'indian' ? 'indian_indicators' : 'crypto_indicators';
    
    let newIndicator = {
        id: Date.now().toString(),
        symbol: targetSymbol,
        type: type,
        timeframe: parseInt(document.getElementById('param-timeframe').value) || 15,
        active: true
    };

    if(type === 'supertrend') {
        newIndicator.period = parseInt(document.getElementById('param-period').value) || 31;
        newIndicator.multiplier = parseFloat(document.getElementById('param-mult').value) || 2.0;
    } else if(type === 'ema') {
        newIndicator.length = parseInt(document.getElementById('param-length').value) || 15;
    } else if(type === 'ema_cross') {
        newIndicator.short = parseInt(document.getElementById('param-short').value) || 9;
        newIndicator.long = parseInt(document.getElementById('param-long').value) || 15;
    } else if(type === 'vwap') {
        newIndicator.source = document.getElementById('param-source').value;
        newIndicator.anchor = document.getElementById('param-anchor').value;
    } else if(type === 'atr') {
        newIndicator.length = parseInt(document.getElementById('param-length').value) || 14;
    } else if(type === 'bb') {
        newIndicator.length = parseInt(document.getElementById('param-length').value) || 20;
        newIndicator.mult = parseFloat(document.getElementById('param-mult').value) || 2.0;
        newIndicator.offset = parseInt(document.getElementById('param-offset').value) || 0;
    }

    configState[key].unshift(newIndicator);
    renderGrid(market, configState[key]);
    saveConfigToBackend();
    updateBackendUsage();
    closeIndicatorModal();
    
    // Log info visually
    let readableType = type === 'supertrend' ? 'Supertrend' : 'EMA Cross';
    showToast(`Successfully deployed ${readableType} strategy for ${targetSymbol}!`);
    console.log(`Deployed new strategy for ${targetSymbol}`);
}

function showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div class="toast-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
        </div>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('toast-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function playHapticSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        if(!ctx) return;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.setValueAtTime(600, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(1000, ctx.currentTime + 0.05);
        gain.gain.setValueAtTime(0.05, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
        osc.start(); osc.stop(ctx.currentTime + 0.1);
    } catch(e) {}
}

async function updateActiveIntelligence() {
    if (!configState) return;
    
    try {
        const res = await fetch(`${API_URL}/live-prices`);
        const prices = await res.json();
        
        const grid = document.getElementById('active-tickers-grid');
        if (!grid) return;

        let activeSymbols = [];
        
        if (configState.indian_enabled) {
            activeSymbols.push(...configState.indian_indicators.filter(ind => ind.active).map(ind => ({ symbol: ind.symbol, market: 'NSE' })));
        }
        
        if (configState.crypto_enabled) {
            activeSymbols.push(...configState.crypto_indicators.filter(ind => ind.active).map(ind => ({ symbol: ind.symbol, market: 'Crypto' })));
        }

        // Deduplicate symbols
        const uniqueSymbols = [];
        const seen = new Set();
        activeSymbols.forEach(s => {
            if (!seen.has(s.symbol)) {
                uniqueSymbols.push(s);
                seen.add(s.symbol);
            }
        });

        if (uniqueSymbols.length === 0) {
            grid.innerHTML = `<div class="no-active-alerts"><p>No symbols in current live stream. Activate a strategy below to start tracking.</p></div>`;
            return;
        }

        // Remove placeholder if it exists
        const placeholder = grid.querySelector('.no-active-alerts');
        if (placeholder) placeholder.remove();

        uniqueSymbols.forEach(item => {
            const currentPrice = prices[item.symbol];
            if (currentPrice === undefined) return;

            let card = document.getElementById(`ticker-${item.symbol}`);
            if (!card) {
                card = document.createElement('div');
                card.id = `ticker-${item.symbol}`;
                card.className = 'ticker-card';
                grid.appendChild(card);
            }

            const prevPrice = previousPrices[item.symbol];
            let priceClass = '';
            let flashClass = '';
            
            if (prevPrice !== undefined && currentPrice !== prevPrice) {
                flashClass = currentPrice > prevPrice ? 'flash-up' : 'flash-down';
                card.classList.remove('flash-up', 'flash-down');
                void card.offsetWidth; // trigger reflow
                card.classList.add(flashClass);
                
                // Remove flash class after animation
                setTimeout(() => card.classList.remove('flash-up', 'flash-down'), 1000);
            }

            const formattedPrice = item.market === 'Crypto' 
                ? `$${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
                : `₹${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

            card.innerHTML = `
                <div class="flash"></div>
                <div class="ticker-info">
                    <span class="ticker-symbol">${item.symbol}</span>
                    <span class="ticker-market">${item.market} Live Feed</span>
                </div>
                <div class="ticker-price">${formattedPrice}</div>
            `;

            previousPrices[item.symbol] = currentPrice;
        });

        // Clean up orphaned cards (if a symbol was removed/deactivated)
        const activeIds = new Set(uniqueSymbols.map(s => `ticker-${s.symbol}`));
        Array.from(grid.children).forEach(child => {
            if (child.id && child.id.startsWith('ticker-') && !activeIds.has(child.id)) {
                child.remove();
            }
        });

    } catch (e) {
        console.error("Live Intelligence sync failed", e);
    }
}

function loadProfileData() {
    const user = {
        name: localStorage.getItem('user_name') || 'TradePulse Trader',
        phone: localStorage.getItem('user_phone') || '+91 98765 43210',
        email: 'demo@example.com',
        tier: 'ELITE'
    };
    
    document.getElementById('profile-name').value = user.name;
    document.getElementById('profile-phone').value = user.phone;
    document.getElementById('profile-email').value = user.email;
    document.getElementById('profile-name-title').innerText = user.name;
    
    // Update header avatar
    const headerAvatar = document.getElementById('header-avatar');
    if(headerAvatar) {
        headerAvatar.style.backgroundImage = `url('https://ui-avatars.com/api/?name=${user.name.split(' ')[0]}&background=3b82f6&color=fff')`;
    }
}

function saveProfile() {
    const name = document.getElementById('profile-name').value;
    const phone = document.getElementById('profile-phone').value;
    
    localStorage.setItem('user_name', name);
    localStorage.setItem('user_phone', phone);
    
    document.getElementById('profile-name-title').innerText = name;
    showToast("Profile updated successfully!");
    
    // Refresh avatar
    loadProfileData();
}

function setActiveNav(text) {
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.innerText.includes(text)) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Subscriptions/Badges shouldn't have active highlight
    document.querySelectorAll('.pro-badge, .profile-nav').forEach(item => {
        if (!item.innerText.includes(text)) {
            item.classList.remove('active');
        }
    });
}

// Optimization for header spacing
window.addEventListener('resize', () => {
    const width = window.innerWidth;
    const navLinks = document.querySelector('.nav-links');
    if(navLinks) {
        navLinks.style.gap = width < 1200 ? '0.8rem' : '1.2rem';
    }
});

// Initial spacing
window.dispatchEvent(new Event('resize'));
