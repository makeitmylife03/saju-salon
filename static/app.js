(() => {
  const cfg = window.SAJU_CONFIG || {};
  if (!cfg.url || !cfg.key || !window.supabase) return;
  const sb = window.supabase.createClient(cfg.url, cfg.key);
  window.sajuSupabase = sb;

  const $ = (s) => document.querySelector(s);
  const msg = (el, text, ok=false) => { if (el) { el.textContent = text; el.className = 'notice ' + (ok ? 'success' : ''); } };

  async function refreshNav() {
    const nav = $('#auth-nav'); if (!nav) return;
    const { data: { session } } = await sb.auth.getSession();
    nav.innerHTML = session
      ? '<span class="logged-email">' + escapeHtml(session.user.email || '') + '</span> <button class="link-btn" id="logout">로그아웃</button>'
      : '<a href="/login">로그인</a>';
    $('#logout')?.addEventListener('click', async () => { await sb.auth.signOut(); location.href='/'; });
  }

  function escapeHtml(v) { return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

  async function loginForm() {
    const form = $('#login-form'); if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = $('#login-email').value.trim();
      const target = $('#login-message');
      const { error } = await sb.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: window.location.origin + '/my' }
      });
      msg(target, error ? error.message : '로그인 링크를 이메일로 보냈습니다. 메일에서 링크를 눌러주세요.', !error);
    });
  }

  async function saveFreshReading() {
    const page = $('#result-page');
    if (!page || page.dataset.fresh !== 'true') return;
    const { data: { session } } = await sb.auth.getSession();
    if (!session) return;
    if (page.dataset.saved === 'true') return;
    const date = document.querySelector('meta[name="saju-birth-date"]')?.content;
    // Fresh data is passed in the page data attributes below.
  }

  async function loadResultPage() {
    const page = $('#result-page'); if (!page) return;
    const readingId = page.dataset.readingId;
    const fresh = page.dataset.fresh === 'true';
    const resultMsg = $('#result-message');

    if (fresh) {
      const birthDate = page.dataset.birthDate;
      const birthTime = page.dataset.birthTime || null;
      const gender = page.dataset.gender || null;
      const { data: { session } } = await sb.auth.getSession();

      if (!session) {
        msg(resultMsg, '무료 결과는 확인할 수 있습니다. 결과를 저장하려면 먼저 로그인해주세요.');
        const btn = $('#detail-button');
        if (btn) { btn.href = '/login'; btn.textContent = '로그인하고 결과 저장하기'; }
        return;
      }

      let calculation = {};
      try {
        const raw = $('#saju-reading-data')?.textContent;
        calculation = raw ? JSON.parse(raw) : {};
      } catch (e) {
        console.error('SAJU DATA PARSE ERROR', e);
      }

      const { data, error } = await sb.from('readings').insert({
        user_id: session.user.id,
        birth_date: birthDate,
        birth_time: birthTime,
        gender,
        free_summary: { summary: calculation.summary || [], teaser: calculation.teaser || {}, calculation }
      }).select('id').single();

      if (error) {
        msg(resultMsg, '결과 저장에 실패했습니다: ' + error.message);
        return;
      }

      page.dataset.readingId = data.id;
      page.dataset.fresh = 'false';

      const btn = $('#detail-button');
      if (btn) btn.href = '/checkout/' + encodeURIComponent(data.id);

      msg(resultMsg, '이 결과는 내 결과에 자동으로 저장되었습니다.', true);
      return;
    }

    if (readingId) await configureResult(readingId);
  }

  function renderSavedTeaser(teaser) {
    const page = $('#result-page');
    if (!page || !teaser) return;
    const cards = (teaser.cards || []).map((card, i) =>
      `<article class="teaser-card"><div class="teaser-number">${i+1}</div><div><h3>${escapeHtml(card.title)}</h3><p>${escapeHtml(card.text)}</p><strong>${escapeHtml(card.hook)}</strong></div></article>`
    ).join('');
    const html = `
      <div class="summary teaser-main">
        <div class="teaser-badge">무료로 확인한 당신의 성향</div>
        <h2>${escapeHtml(teaser.headline || '')}</h2>
        <p class="teaser-intro">${escapeHtml(teaser.intro || '')}</p>
        ${cards}
        <div class="teaser-question"><span>잠깐</span><b>“${escapeHtml(teaser.question || '')}”</b><p>이 질문에 대한 답은 여러 기운의 관계와 시기까지 함께 봐야 합니다.</p></div>
      </div>`;
    const anchor = $('.technical-details');
    if (anchor) anchor.insertAdjacentHTML('beforebegin', html);
    else {
      const list = $('#summary-list');
      if (list) {
        const wrapper = list.closest('.summary');
        if (wrapper) wrapper.outerHTML = html;
      }
    }
  }
  async function configureResult(readingId) {
    const resultMsg = $('#result-message');
    const { data: { session } } = await sb.auth.getSession();
    if (!session) {
      $('#detail-button').href = '/login';
      msg(resultMsg, '로그인하면 저장된 결과를 확인할 수 있습니다.');
      return;
    }
    const { data: reading, error } = await sb.from('readings').select('id,birth_date,birth_time,gender,free_summary').eq('id', readingId).single();
    if (error || !reading) { msg(resultMsg, '결과를 찾을 수 없습니다.'); return; }
    $('#reading-meta').textContent = reading.birth_date + (reading.birth_time ? ' · ' + reading.birth_time : '');
    const saved = reading.free_summary || {};
    if (Array.isArray(saved)) {
      $('#summary-list').innerHTML = saved.map((line, i) => `<div class="summary-line"><b>${i+1}</b><p>${escapeHtml(line)}</p></div>`).join('');
    } else if (saved.teaser) {
      renderSavedTeaser(saved.teaser);
    }

    const { data: orders, error: orderError } = await sb.from('orders').select('reading_id,status').eq('reading_id', readingId).eq('status','PAID').limit(1);
    if (orderError) console.error('ORDER CHECK ERROR', orderError);
    if (orders?.length) {
      let { data: report, error: reportError } = await sb.from('paid_reports').select('report').eq('reading_id', readingId).single();
      if (reportError) console.error('PAID REPORT ERROR', reportError);

      // 이전에 생성된 짧은 리포트가 저장되어 있으면 새 상세 리포트로 한 번만 갱신합니다.
      if (report?.report && Number(report.report._version || 0) < 4) {
        try {
          const refresh = await fetch('/payment/regenerate-report', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + session.access_token
            },
            body: JSON.stringify({ reading_id: readingId })
          });
          const refreshed = await refresh.json();
          if (refresh.ok && refreshed.report) {
            report = { report: refreshed.report };
          } else {
            console.error('REPORT REGENERATE ERROR', refreshed);
          }
        } catch (e) {
          console.error('REPORT REGENERATE REQUEST ERROR', e);
        }
      }

      if (report?.report) {
        $('#locked-report').classList.add('hidden');
        $('#paid-report').classList.remove('hidden');
        $('#paid-report-content').innerHTML = renderReport(report.report);
        return;
      }
    }
    $('#detail-button').href = '/checkout/' + encodeURIComponent(readingId);
  }

  function renderReport(report) {
    const r = report || {};
    const sections = Object.entries(r).filter(([k]) => k !== '_version');
    if (!sections.length) return '<p>상세 리포트가 준비 중입니다.</p>';
    const order = [
      '한눈에 보는 핵심','내 사주의 구조','타고난 성향','돈과 재물','직업과 사업',
      '연애와 인간관계','반복되기 쉬운 패턴','내가 조심할 부분','대운과 시기',
      '지금 가장 먼저 점검할 5가지','내 사주를 실제 생활에 적용한다면','현실적인 조언','마지막으로'
    ];
    const sorted = [
      ...order.filter(k => r[k] !== undefined).map(k => [k, r[k]]),
      ...sections.filter(([k]) => !order.includes(k))
    ];
    const toc = sorted.map(([k], i) => '<a href="#report-section-' + i + '" class="report-toc-item"><span>' + String(i + 1).padStart(2,'0') + '</span>' + escapeHtml(k) + '</a>').join('');
    const body = sorted.map(([k,v], i) => {
      let text = escapeHtml(typeof v === 'string' ? v : JSON.stringify(v));
      text = text.replace(/&lt;strong&gt;/g, '<strong>').replace(/&lt;\\/strong&gt;/g, '</strong>');
      const paragraphs = text.split(/\\n\\n|\\n/).filter(Boolean).map(p => '<p>' + p + '</p>').join('');
      return '<article id="report-section-' + i + '" class="report-section"><h3>' + escapeHtml(k) + '</h3>' + paragraphs + '</article>';
    }).join('');
    return '<nav class="report-toc" aria-label="상세 리포트 목차">' + toc + '</nav>' + body;
  }

  async function loadCheckout() {
    const box = $('#checkout');
    if (!box) return;
    const button = $('#pay-button');
    const target = $('#checkout-message');
    const readingId = box.dataset.readingId;
    const productName = box.dataset.productName || '사주 상세 리포트';

    const { data: { session } } = await sb.auth.getSession();
    if (!session) {
      msg(target, '로그인 후 결제할 수 있습니다.');
      if (button) {
        button.textContent = '로그인하기';
        button.onclick = () => { location.href = '/login'; };
      }
      return;
    }

    if (!cfg.tossClientKey || !window.TossPayments) {
      msg(target, '토스 결제 설정이 아직 완료되지 않았습니다.');
      return;
    }

    button?.addEventListener('click', async () => {
      button.disabled = true;
      msg(target, '결제창을 준비하고 있습니다...', true);
      try {
        const orderResponse = await fetch('/payment/create-order', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + session.access_token
          },
          body: JSON.stringify({ reading_id: readingId })
        });
        const order = await orderResponse.json();
        if (!orderResponse.ok) throw new Error(order.error || '주문 생성에 실패했습니다.');

        const tossPayments = TossPayments(cfg.tossClientKey);
        const payment = tossPayments.payment({ customerKey: crypto.randomUUID() });

        await payment.requestPayment({
          method: 'CARD',
          amount: { value: order.amount, currency: 'KRW' },
          orderId: order.order_id,
          orderName: productName,
          customerEmail: session.user.email || undefined,
          successUrl: window.location.origin + '/payment/success',
          failUrl: window.location.origin + '/payment/fail'
        });
      } catch (error) {
        console.error('TOSS PAYMENT ERROR', error);
        msg(target, error?.message || '결제를 시작하지 못했습니다.');
        button.disabled = false;
      }
    });
  }

  async function loadMy() {
    const box = $('#my-readings'); if (!box) return;
    const auth = $('#my-auth');
    const { data: { session } } = await sb.auth.getSession();
    if (!session) {
      auth.innerHTML = '<a class="btn" href="/login">로그인하기</a>';
      return;
    }
    auth.innerHTML = '<p class="success-text">' + escapeHtml(session.user.email || '') + '으로 로그인되어 있습니다.</p>';
    const { data, error } = await sb.from('readings').select('id,birth_date,birth_time,created_at').order('created_at', { ascending:false });
    if (error) { box.textContent = error.message; return; }
    if (!data?.length) { box.innerHTML = '<p class="muted">아직 저장된 사주 결과가 없습니다.</p>'; return; }
    box.innerHTML = data.map(r => `<a class="reading-item" href="/saju/result/${r.id}"><strong>${escapeHtml(r.birth_date)}</strong><span>${r.birth_time ? escapeHtml(r.birth_time) : '출생시간 미입력'}</span><em>결과 보기 →</em></a>`).join('');
  }

  async function init() {
    await refreshNav();
    await loginForm();
    await loadMy();
    await loadCheckout();
    await loadResultPage();
  }
  init();
})();
