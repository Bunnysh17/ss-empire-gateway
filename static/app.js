// TerminalX & UPI Payment Gateway Client Logic

let currentOrderId = null;
let currentQrInstance = null;
let pollInterval = null;
let countdownInterval = null;
let remainingSeconds = 600;

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initAmountChips();
  initForms();
  // Only run Admin Panel logic if on admin page
  if (document.getElementById('txnTableBody') || document.getElementById('settingToken')) {
    loadConfig();
    loadTransactions();
    checkTerminalXStatus();
    initApiDocs();
    document.getElementById('btnRefreshTxns')?.addEventListener('click', loadTransactions);
    document.getElementById('btnCheckApi')?.addEventListener('click', checkTerminalXStatus);
    document.getElementById('btnTestDiagnostics')?.addEventListener('click', runDiagnostics);
  }

  // Modal Close buttons
  document.getElementById('modalCloseBtn')?.addEventListener('click', closePaymentModal);
  document.getElementById('receiptCloseBtn')?.addEventListener('click', () => {
    document.getElementById('successModal').classList.remove('show');
    loadTransactions();
  });

  // Verify UTR button
  document.getElementById('btnVerifyUtr')?.addEventListener('click', async () => {
    if (!currentOrderId) return;
    const utr = document.getElementById('utrInput').value.trim();
    if (!utr || utr.length < 10) {
      showToast("Please enter a valid 12-digit UTR Number", "error");
      return;
    }
    const btn = document.getElementById('btnVerifyUtr');
    btn.disabled = true;
    btn.textContent = "Verifying...";
    try {
      const resp = await fetch('/api/verify-utr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: currentOrderId, utr: utr })
      });
      const data = await resp.json();
      btn.disabled = false;
      btn.textContent = "Verify UTR";
      if (data.success) {
        closePaymentModal();
        showReceipt(data.order);
        showToast("Payment verified via UTR!", "info");
      } else {
        showToast(data.message || "UTR Verification failed", "error");
      }
    } catch (e) {
      btn.disabled = false;
      btn.textContent = "Verify UTR";
      showToast("Network error submitting UTR", "error");
    }
  });

  // Simulate Payment Success
  document.getElementById('btnSimulateSuccess')?.addEventListener('click', simulateCurrentPayment);

  // Copy link
  document.getElementById('btnCopyLink')?.addEventListener('click', () => {
    const input = document.getElementById('generatedLinkInput');
    input.select();
    navigator.clipboard.writeText(input.value);
    showToast('Payment link copied to clipboard!');
  });

  // Clear old pending transactions
  document.getElementById('btnClearDemoTxns')?.addEventListener('click', async () => {
    if (!confirm('Purani pending history clear karein? Real verified payments (with bank UTR) safe rahengi.')) return;
    try {
      const resp = await fetch('/api/transactions/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keep_real: true })
      });
      const data = await resp.json();
      showToast(data.message || 'Transactions cleared!');
      loadTransactions();
    } catch (e) {
      showToast('Error clearing transactions', 'error');
    }
  });
});

/* Tabs Switching */
function initTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetId = `panel-${btn.dataset.tab}`;
      document.getElementById(targetId)?.classList.add('active');

      if (btn.dataset.tab === 'transactions') {
        loadTransactions();
      }
    });
  });
}

/* Quick Amount Chips & Live Amount Handling */
function initAmountChips() {
  const chips = document.querySelectorAll('.amount-chip');
  const amountInput = document.getElementById('custAmount');
  const payBtnText = document.getElementById('btnPayText');

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const val = chip.dataset.val;
      if (amountInput) {
        amountInput.value = val;
      }
      if (payBtnText) {
        payBtnText.textContent = `Pay ₹${val} with UPI`;
      }
    });
  });

  if (amountInput) {
    amountInput.addEventListener('input', () => {
      const val = amountInput.value.trim();
      chips.forEach(c => {
        if (c.dataset.val === val) {
          c.classList.add('active');
        } else {
          c.classList.remove('active');
        }
      });
      if (payBtnText) {
        payBtnText.textContent = val && parseInt(val) > 0 ? `Pay ₹${val} with UPI` : 'Proceed to Pay';
      }
    });
  }
}

/* Forms Setup */
function initForms() {
  // Checkout Form Submit -> Direct Redirect to /pay
  const checkoutForm = document.getElementById('checkoutForm');
  checkoutForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btnPayNow');
    const amount = document.getElementById('custAmount')?.value || '1';
    const remark = document.getElementById('custRemark')?.value || 'Service Payment';

    btn.disabled = true;
    btn.innerHTML = `<span class="spinner" style="width:18px; height:18px; display:inline-block; border:2px solid rgba(255,255,255,0.3); border-top-color:#fff; border-radius:50%; animation:spin 0.8s linear infinite; margin-right:8px;"></span> Opening Secure Checkout...`;

    const payload = {
      customer_name: 'Direct Customer',
      customer_mobile: '9876543210',
      amount: amount,
      remark: remark
    };

    try {
      const resp = await fetch('/api/create-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (data.success && data.order_id) {
        window.location.href = `/pay?id=${encodeURIComponent(data.order_id)}&amount=${encodeURIComponent(amount)}&desc=${encodeURIComponent(remark)}`;
      } else {
        window.location.href = `/pay?amount=${encodeURIComponent(amount)}&desc=${encodeURIComponent(remark)}`;
      }
    } catch (err) {
      window.location.href = `/pay?amount=${encodeURIComponent(amount)}&desc=${encodeURIComponent(remark)}`;
    }
  });

  // Payment Link Generator Form
  const linkForm = document.getElementById('linkForm');
  linkForm?.addEventListener('submit', (e) => {
    e.preventDefault();
    const amount = document.getElementById('linkAmount').value;
    const desc = encodeURIComponent(document.getElementById('linkDesc').value);
    const origin = window.location.origin;
    const orderId = 'TXN' + Math.floor(Date.now() / 1000);
    const link = `${origin}/pay?id=${orderId}&amount=${amount}&desc=${desc}`;

    document.getElementById('generatedLinkInput').value = link;
    document.getElementById('btnOpenLink').href = link;
    document.getElementById('generatedLinkBox').style.display = 'block';
    showToast('Payment link created successfully!');
  });

  // Settings Form Submit
  const settingsForm = document.getElementById('settingsForm');
  settingsForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      user_token: document.getElementById('settingToken').value,
      mode: document.getElementById('settingMode').value,
      merchant_upi: document.getElementById('settingMerchantUpi').value,
      merchant_name: document.getElementById('settingMerchantName').value,
      webhook_url: document.getElementById('settingWebhook').value,
      discord_bot_webhook_url: document.getElementById('settingDiscordBotWebhook')?.value || '',
      discord_bot_token: document.getElementById('settingDiscordBotToken')?.value || '',
      discord_proof_channel_id: document.getElementById('settingDiscordProofChannelId')?.value || ''
    };

    try {
      const resp = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const res = await resp.json();
      if (res.success) {
        showToast('Settings saved successfully!');
        checkTerminalXStatus();
      }
    } catch (e) {
      showToast('Error saving settings', 'error');
    }
  });

  // Test Discord Proof Button
  const btnTestBot = document.getElementById('btnTestDiscordWebhook');
  btnTestBot?.addEventListener('click', async () => {
    btnTestBot.disabled = true;
    const origText = btnTestBot.textContent;
    btnTestBot.textContent = '⏳ Sending Proof...';
    try {
      showToast('Sending test payment proof to Discord channel...');
      const resp = await fetch('/api/test-discord-bot-webhook', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: 'TXN' + Math.floor(Date.now() / 1000),
          amount: '100',
          utr: '760366829987',
          customer_name: 'Test Customer',
          remark: 'Discord_Test'
        })
      });
      const data = await resp.json();
      if (data.success) {
        showToast('✅ Payment Proof announced directly in Discord channel!');
      } else {
        const err = data.results?.direct_discord_api?.error || data.results?.direct_discord_api?.response || 'Failed to post proof';
        showToast('⚠️ Discord Proof Error: ' + err, 'error');
      }
    } catch (e) {
      showToast('Error connecting to gateway: ' + e.message, 'error');
    } finally {
      btnTestBot.disabled = false;
      btnTestBot.textContent = origText;
    }
  });
}

/* Open Payment Modal */
function openPaymentModal(orderData) {
  currentOrderId = orderData.order_id;
  document.getElementById('modalAmount').textContent = orderData.amount;
  document.getElementById('modalOrderId').textContent = orderData.order_id;

  const qrContainer = document.getElementById('modalQrCode');
  qrContainer.innerHTML = '';

  const qrString = orderData.upi_intent || orderData.qr_data || orderData.payment_url;

  currentQrInstance = new QRCode(qrContainer, {
    text: qrString,
    width: 200,
    height: 200,
    colorDark: "#000000",
    colorLight: "#ffffff",
    correctLevel: QRCode.CorrectLevel.M
  });

  // Setup deep-links for mobile UPI apps
  const intent = orderData.upi_intent || qrString;
  document.getElementById('btnGpay').href = intent;
  document.getElementById('btnPhonepe').href = intent;
  document.getElementById('btnPaytm').href = intent;

  // TerminalX payment URL button
  const btnTx = document.getElementById('btnOpenTerminalxCheckout');
    btnTx.href = `/pay?id=${orderData.order_id}&amount=${orderData.amount}&desc=Payment`;
    btnTx.style.display = 'inline-flex';

  // Inform about routing mode
  if (orderData.mode === 'terminalx') {
    document.getElementById('pollingStatusText').textContent = 'Live TerminalX Gateway Active (Scan QR or open payment page)';
  } else if (orderData.terminalx_error) {
    document.getElementById('pollingStatusText').textContent = 'Direct UPI Mode (' + orderData.terminalx_error + ')';
  } else {
    document.getElementById('pollingStatusText').textContent = 'Awaiting payment confirmation...';
  }

  // Start timer and polling
  startModalCountdown();
  startPaymentPolling(orderData.order_id);

  document.getElementById('paymentModal').classList.add('show');
}

function closePaymentModal() {
  document.getElementById('paymentModal').classList.remove('show');
  if (pollInterval) clearInterval(pollInterval);
  if (countdownInterval) clearInterval(countdownInterval);
  currentOrderId = null;
}

function startModalCountdown() {
  remainingSeconds = 600;
  const timerEl = document.getElementById('modalTimer');
  if (countdownInterval) clearInterval(countdownInterval);

  countdownInterval = setInterval(() => {
    remainingSeconds--;
    if (remainingSeconds <= 0) {
      clearInterval(countdownInterval);
      timerEl.textContent = '00:00 (Expired)';
      if (pollInterval) clearInterval(pollInterval);
    } else {
      const mins = String(Math.floor(remainingSeconds / 60)).padStart(2, '0');
      const secs = String(remainingSeconds % 60).padStart(2, '0');
      timerEl.textContent = `${mins}:${secs}`;
    }
  }, 1000);
}

function startPaymentPolling(orderId) {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    try {
      const resp = await fetch('/api/check-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId })
      });
      const data = await resp.json();

      if (data.status === 'SUCCESS' || data.status === 'COMPLETED') {
        clearInterval(pollInterval);
        closePaymentModal();
        showReceipt(data);
      }
    } catch (e) {
      console.warn("Polling status error", e);
    }
  }, 3000);
}

/* Simulate Payment for Testing */
async function simulateCurrentPayment() {
  if (!currentOrderId) return;
  try {
    const resp = await fetch('/api/simulate-success', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: currentOrderId })
    });
    const data = await resp.json();
    if (data.success) {
      closePaymentModal();
      showReceipt(data.order);
      showToast('Payment verified via test simulator!');
    }
  } catch (e) {
    showToast('Simulation error', 'error');
  }
}

/* Show Receipt Modal */
function showReceipt(txn) {
  document.getElementById('receiptAmount').textContent = '₹' + (txn.amount || '0');
  document.getElementById('receiptOrderId').textContent = txn.order_id || '-';
  document.getElementById('receiptUtr').textContent = txn.utr || ('UPI' + Math.floor(Date.now() / 1000));
  document.getElementById('receiptDate').textContent = txn.date || new Date().toLocaleString();

  document.getElementById('successModal').classList.add('show');

  // Trigger celebration confetti
  try {
    confetti({
      particleCount: 80,
      spread: 60,
      origin: { y: 0.6 }
    });
  } catch (e) {}
}

/* Check TerminalX Status */
async function checkTerminalXStatus() {
  const dot = document.getElementById('apiStatusDot');
  const text = document.getElementById('apiStatusText');

  text.textContent = 'Testing Token...';
  dot.className = 'status-dot';

  try {
    const resp = await fetch('/api/test-terminalx');
    const data = await resp.json();

    if (data.is_active) {
      dot.className = 'status-dot active';
      text.textContent = 'TerminalX Token: Active';
    } else {
      dot.className = 'status-dot danger';
      text.textContent = `TerminalX: ${data.message || 'Inactive'}`;
    }
  } catch (e) {
    dot.className = 'status-dot danger';
    text.textContent = 'TerminalX: Server Offline';
  }
}

/* Run Diagnostics in Settings Tab */
async function runDiagnostics() {
  const box = document.getElementById('diagnosticsBox');
  const out = document.getElementById('diagnosticsOutput');
  box.style.display = 'block';
  out.textContent = 'Connecting to https://terminalx999.space/api/create-order...\nTesting token response...';

  try {
    const resp = await fetch('/api/test-terminalx');
    const data = await resp.json();
    out.textContent = JSON.stringify(data, null, 2);
    if (!data.is_active) {
      out.textContent += `\n\n--> DIAGNOSIS: ${data.message}\n--> ACTION: Tell Suyash/Admin to renew or activate the plan on terminalx999.space.`;
    }
  } catch (e) {
    out.textContent = 'Connection Error: ' + e.message;
  }
}

/* Load Settings */
async function loadConfig() {
  try {
    const resp = await fetch('/api/config');
    const data = await resp.json();
    if (data.success && data.config) {
      const cfg = data.config;
      document.getElementById('settingToken').value = cfg.user_token || '';
      document.getElementById('settingMode').value = cfg.mode || 'hybrid';
      document.getElementById('settingMerchantUpi').value = cfg.merchant_upi || '';
      document.getElementById('settingMerchantName').value = cfg.merchant_name || '';
      document.getElementById('settingWebhook').value = cfg.webhook_url || '';
      if (document.getElementById('settingDiscordProofChannelId')) {
        document.getElementById('settingDiscordProofChannelId').value = cfg.discord_proof_channel_id || '1503017156541943838';
      }
      if (document.getElementById('settingDiscordBotToken')) {
        document.getElementById('settingDiscordBotToken').value = cfg.discord_bot_token || '';
      }
      if (document.getElementById('settingDiscordBotWebhook')) {
        document.getElementById('settingDiscordBotWebhook').value = cfg.discord_bot_webhook_url || 'http://127.0.0.1:10000/api/payment-webhook';
      }
    }
  } catch (e) {}
}

/* Load Transactions Table */
async function loadTransactions() {
  const tbody = document.getElementById('txnTableBody');
  try {
    const resp = await fetch('/api/transactions');
    const data = await resp.json();

    if (!data.transactions || data.transactions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:24px;">No transactions recorded yet. Create an order to see it here!</td></tr>`;
      return;
    }

    // Sort: Verified SUCCESS payments with real UTRs first, then newest
    const sortedTxns = [...data.transactions].sort((a, b) => {
      const aSuccess = (a.status === 'SUCCESS' || a.status === 'COMPLETED') ? 1 : 0;
      const bSuccess = (b.status === 'SUCCESS' || b.status === 'COMPLETED') ? 1 : 0;
      if (bSuccess !== aSuccess) return bSuccess - aSuccess;
      return (b.date || '').localeCompare(a.date || '');
    });

    tbody.innerHTML = sortedTxns.map(t => {
      const isSuccess = t.status === 'SUCCESS' || t.status === 'COMPLETED';
      let badgeClass = 'badge-pending';
      if (isSuccess) badgeClass = 'badge-success';
      if (t.status === 'FAILED') badgeClass = 'badge-failed';

      const engineBadge = t.engine === 'terminalx' 
        ? `<span style="color:var(--primary); font-size:0.75rem; font-weight:600;">TerminalX</span>`
        : `<span style="color:#a855f7; font-size:0.75rem; font-weight:600;">Direct UPI</span>`;

      const rowStyle = isSuccess 
        ? `background: rgba(0, 230, 118, 0.04); border-left: 3px solid #00e676;` 
        : ``;

      return `
        <tr style="${rowStyle}">
          <td style="font-family:monospace; font-weight:600; color:#fff;">${t.order_id}</td>
          <td>${t.customer_name || 'Customer'}<br><small style="color:var(--text-muted);">${t.customer_mobile || ''}</small></td>
          <td style="font-weight:700; color:${isSuccess ? '#00e676' : '#fff'};">₹${t.amount}</td>
          <td>${engineBadge}</td>
          <td><span class="badge ${badgeClass}">${t.status}</span></td>
          <td style="font-family:monospace; font-size:0.82rem; font-weight:700; color:${isSuccess ? '#00e676' : 'var(--text-muted)'};">${t.utr || '-'}</td>
          <td style="font-size:0.8rem; color:var(--text-muted);">${t.date || '-'}</td>
          <td>
            ${t.status === 'PENDING' ? `
              <button class="btn btn-secondary btn-sm" onclick="checkLiveTxnStatus('${t.order_id}')" style="padding:4px 10px; font-size:0.75rem;">
                Check Status
              </button>
            ` : `<span style="color:#00e676; font-size:0.8rem; font-weight:700; display:inline-flex; align-items:center; gap:4px;">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00e676" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  Verified Real
                 </span>`}
          </td>
        </tr>
      `;
    }).join('');

  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--danger);">Error loading transactions</td></tr>`;
  }
}

window.checkLiveTxnStatus = async function(orderId) {
  try {
    showToast(`Checking status for ${orderId}...`);
    const resp = await fetch('/api/check-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: orderId })
    });
    const d = await resp.json();
    if (d.status === 'SUCCESS' || d.status === 'COMPLETED') {
      showToast(`Order ${orderId} is PAID! UTR: ${d.utr || 'Verified'}`);
    } else {
      showToast(`Order ${orderId} is currently ${d.status}`);
    }
    loadTransactions();
  } catch (e) {
    showToast('Error checking order status', 'error');
  }
};

/* Toast Helper */
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = 'toast';
  if (type === 'error') {
    toast.style.borderLeftColor = 'var(--danger)';
  }
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* Init API SDK Snippet Tabs & Copy buttons in Admin Panel */
function initApiDocs() {
  const sdkTabs = document.querySelectorAll('.sdk-tab-btn');
  const codeBoxes = document.querySelectorAll('.sdk-code-box');

  sdkTabs.forEach(btn => {
    btn.addEventListener('click', () => {
      sdkTabs.forEach(b => {
        b.classList.remove('active', 'btn-primary');
        b.classList.add('btn-secondary');
      });
      btn.classList.add('active', 'btn-primary');
      btn.classList.remove('btn-secondary');

      const targetId = `code-${btn.dataset.sdk}`;
      codeBoxes.forEach(box => {
        if (box.id === targetId) {
          box.style.display = 'block';
        } else {
          box.style.display = 'none';
        }
      });
    });
  });

  // Copy buttons for Base URLs
  document.querySelectorAll('.btn-copy-api').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const input = document.getElementById(targetId);
      if (input) {
        input.select();
        navigator.clipboard.writeText(input.value);
        const originalText = btn.textContent;
        btn.textContent = '✅ Copied!';
        setTimeout(() => { btn.textContent = originalText; }, 2000);
        showToast('URL copied to clipboard!');
      }
    });
  });

  // Copy button for Active Code
  document.getElementById('btnCopyActiveCode')?.addEventListener('click', () => {
    const activeBox = document.querySelector('.sdk-code-box[style*="block"]') || document.getElementById('code-python');
    if (activeBox) {
      navigator.clipboard.writeText(activeBox.textContent);
      const btn = document.getElementById('btnCopyActiveCode');
      const originalText = btn.textContent;
      btn.textContent = '✅ Code Copied!';
      setTimeout(() => { btn.textContent = originalText; }, 2000);
      showToast('Code snippet copied to clipboard!');
    }
  });
}

