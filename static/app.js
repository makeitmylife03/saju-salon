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
    const anchor = $('.technical-details');
    if (!page || !teaser || !anchor) return;
    const cards = (teaser.cards || []).map((card, i) =>
      `<article class="teaser-card"><div class="teaser-number">${i+1}</div><div><h3>${escapeHtml(card.title)}</h3><p>${escapeHtml(card.text)}</p><strong>${escapeHtml(card.hook)}</strong></div></article>`
    ).join('');
    const locked = (teaser.locked_points || []).map(x => `<div>🔒 ${escapeHtml(x)}</div>`).join('');
    anchor.insertAdjacentHTML('beforebegin', `
      <div class="summary teaser-main">
        <div class="teaser-badge">무료로 확인한 당신의 성향</div>
        <h2>${escapeHtml(teaser.headline || '')}</h2>
        <p class="teaser-intro">${escapeHtml(teaser.intro || '')}</p>
        ${cards}
        <div class="teaser-question"><span>잠깐</span><b>“${escapeHtml(teaser.question || '')}”</b><p>이 질문에 대한 답은 여러 기운의 관계와 시기까지 함께 봐야 합니다.</p></div>
      </div>
    `);
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

    const { data: orders } = await sb.from('orders').select('reading_id,status').eq('reading_id', readingId).eq('status','PAID').limit(1);
    if (orders?.length) {
      const { data: report } = await sb.from('paid_reports').select('report').eq('reading_id', readingId).single();
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
    const sections = Object.entries(r);
    if (!sections.length) return '<p>상세 리포트가 준비 중입니다.</p>';
    return sections.map(([k,v]) => `<article class="report-section"><h3>${escapeHtml(k)}</h3><p>${escapeHtml(typeof v === 'string' ? v : JSON.stringify(v))}</p></article>`).join('');
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
    await loadResultPage();
  }
  init();
})();
