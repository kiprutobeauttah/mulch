(() => {
  const MODELS = JSON.parse(document.getElementById('modelData').textContent);
  const $ = (id) => document.getElementById(id);

  const ICON_CACHE = {};
  async function hydrateIcons(root = document) {
    const nodes = Array.from(root.querySelectorAll('[data-icon]:not([data-loaded])'));
    if (!nodes.length) return;
    const names = [...new Set(nodes.map((n) => n.dataset.icon))];
    const fetched = {};
    await Promise.all(names.map(async (name) => {
      if (ICON_CACHE[name]) { fetched[name] = ICON_CACHE[name]; return; }
      try {
        const res = await fetch('/icons/' + name + '.svg');
        const txt = await res.text();
        const svg = new DOMParser().parseFromString(txt, 'image/svg+xml').querySelector('svg');
        if (svg) svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        ICON_CACHE[name] = fetched[name] = svg ? svg.outerHTML : '';
      } catch { fetched[name] = ''; }
    }));
    nodes.forEach((el) => {
      if (fetched[el.dataset.icon]) el.innerHTML = fetched[el.dataset.icon];
      el.setAttribute('data-loaded', '1');
    });
  }

  const stage = $('stage');
  const fileInput = $('fileInput');
  const dropzoneInner = $('dropzoneInner');
  const imageWrap = $('imageWrap');
  const image = $('image');
  const removeBtn = $('removeBtn');
  const imageCaption = $('imageCaption');
  const analyzeBtn = $('analyzeBtn');
  const btnLabel = $('btnLabel');
  const spinner = analyzeBtn.querySelector('.spinner');
  const modelSelect = $('modelSelect');
  const modelNote = $('modelNote');
  const modelStatus = $('modelStatus');
  const printBtn = $('printBtn');
  const recordsBtn = $('recordsBtn');
  const viewToggle = $('viewToggle');
  const viewBtns = Array.from(document.querySelectorAll('.view-btn'));

  const patientName = $('patientName');
  const patientMrn = $('patientMrn');
  const patientSex = $('patientSex');
  const scanDate = $('scanDate');

  const resultEmpty = $('resultEmpty');
  const reportBody = $('reportBody');
  const resultError = $('resultError');
  const caseTag = $('caseTag');
  const verdictBadge = $('verdictBadge');
  const gaugeArc = $('gaugeArc');
  const gaugeVal = $('gaugeVal');
  const interpretation = $('interpretation');
  const patientLine = $('patientLine');
  const pNameLine = $('pNameLine');
  const pMetaLine = $('pMetaLine');
  const metaTime = $('metaTime');
  const metaSaved = $('metaSaved');

  const outModel = $('outModel');
  const outNormProb = $('outNormProb');
  const outPneuProb = $('outPneuProb');
  const outLevel = $('outLevel');
  const outLatency = $('outLatency');
  const outCaseId = $('outCaseId');
  const printDate = $('printDate');
  const printCaseId = $('printCaseId');
  const storagePath = $('storagePath');
  const storageInput = $('storageInput');
  const storageForm = $('storageForm');
  const storageSet = $('storageSet');
  const storageReset = $('storageReset');
  const storageCancel = $('storageCancel');
  const storageMsg = $('storageMsg');

  const recordsOverlay = $('recordsOverlay');
  const closeRecords = $('closeRecords');
  const recordSearch = $('recordSearch');
  const recordCount = $('recordCount');
  const recordsList = $('recordsList');
  const recordsEmpty = $('recordsEmpty');

  let selectedFile = null;
  let fileUrl = null;
  let currentView = 'original';
  let currentResult = null;

  const LEVEL_TEXT = {
    high: 'Confident automated finding.',
    medium: 'Moderate certainty- correlate with clinical context.',
    low: 'Ambiguous pattern- verify manually before acting.',
  };

  const DX_ICON = { NORMAL: 'check-circle', PNEUMONIA: 'alert-triangle' };

  function formatPct(v) { return (v * 100).toFixed(1) + '%'; }
  function fmtLatency(ms) { return ms >= 1000 ? (ms / 1000).toFixed(1) + ' s' : ms + ' ms'; }

  function setModelNote() {
    const m = MODELS.find((x) => x.key === modelSelect.value);
    modelNote.textContent = m ? m.note : '';
  }

  function showError(msg) {
    resultError.textContent = msg;
    resultError.classList.add('show');
  }
  function hideError() { resultError.classList.remove('show'); }

  function patientSummary() {
    const parts = [];
    if (patientMrn.value.trim()) parts.push('MRN ' + patientMrn.value.trim());
    if (patientSex.value) parts.push(patientSex.value);
    return parts.join(' · ');
  }

  function setImage(src, caption) {
    image.src = src;
    imageCaption.textContent = caption || '';
    imageCaption.style.display = caption ? '' : 'none';
    imageWrap.hidden = false;
    dropzoneInner.hidden = true;
  }

  function updateView() {
    const r = currentResult;
    if (imageWrap.hidden) return;
    if (currentView === 'heatmap') {
      if (r && r.heatmap_url) { setImage(r.heatmap_url, 'ATTENTION'); return; }
    } else if (currentView === 'overlay') {
      if (r && r.overlay_url) { setImage(r.overlay_url, 'ATTENTION OVERLAY'); return; }
    }
    if (r && r.image_url) { setImage(r.image_url, currentResult ? 'X-RAY' : ''); return; }
    if (fileUrl) { setImage(fileUrl); return; }
    if (selectedFile) { if (!fileUrl) fileUrl = URL.createObjectURL(selectedFile); setImage(fileUrl); }
    viewBtns.forEach((b) => b.classList.toggle('active', b.dataset.view === currentView));
    viewToggle.hidden = !(r && r.overlay_url);
  }

  function selectFile(file) {
    if (!file) return;
    if (!file.type.startsWith('image/')) { showError('Please choose an image file (PNG or JPG).'); return; }
    if (file.size > 16 * 1024 * 1024) { showError('Image is too large (max 16 MB).'); return; }

    selectedFile = file;
    currentResult = null;
    currentView = 'original';
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    fileUrl = URL.createObjectURL(file);

    hideError();
    resultEmpty.hidden = false;
    reportBody.hidden = true;
    caseTag.hidden = true;
    printBtn.disabled = true;
    analyzeBtn.disabled = false;
    stage.classList.add('has-image');
    updateView();
  }

  function clearSelection() {
    selectedFile = null;
    currentResult = null;
    currentView = 'original';
    if (fileUrl) URL.revokeObjectURL(fileUrl);
    fileUrl = null;
    imageWrap.hidden = true;
    dropzoneInner.hidden = false;
    stage.classList.remove('has-image');
    analyzeBtn.disabled = true;
    printBtn.disabled = true;
    viewToggle.hidden = true;
    resultEmpty.hidden = false;
    reportBody.hidden = true;
    caseTag.hidden = true;
    hideError();
  }

  function setGauge(confidence) {
    const pct = Math.round(confidence * 100);
    gaugeVal.textContent = pct + '%';
    gaugeArc.style.strokeDashoffset = String(100 - pct);
    gaugeArc.style.stroke = pct >= 80 ? '#0e8a70' : pct >= 60 ? '#c2410c' : '#b45309';
  }

  function setDiagnosis(verdict) {
    verdictBadge.textContent = verdict;
    verdictBadge.classList.remove('normal', 'pneumonia', 'placeholder');
    verdictBadge.classList.add(verdict === 'PNEUMONIA' ? 'pneumonia' : 'normal');
    const badge = verdictBadge;
    const existing = badge.querySelector('i');
    const icon = document.createElement('i');
    icon.className = 'ic';
    icon.setAttribute('data-icon', DX_ICON[verdict] || 'activity');
    if (existing) badge.replaceChild(icon, existing); else badge.prepend(icon);
    hydrateIcons(badge);
  }

  function renderResult(r) {
    hideError();
    resultEmpty.hidden = true;
    reportBody.hidden = false;
    printBtn.disabled = false;

    setDiagnosis(r.diagnosis || r.verdict);
    setGauge(r.confidence || 0);

    const level = (r.confidence_level || 'low').toLowerCase();
    outLevel.textContent = level;
    outLevel.style.color = level === 'high' ? 'var(--normal)' : level === 'medium' ? 'var(--pneumonia-strong)' : 'var(--low)';

    outModel.textContent = r.model_label || '—';
    const probs = r.probabilities || {
      NORMAL: r.probability_normal,
      PNEUMONIA: r.probability_pneumonia,
    };
    outNormProb.textContent = formatPct(probs?.NORMAL ?? 0);
    outPneuProb.textContent = formatPct(probs?.PNEUMONIA ?? 0);
    outLatency.textContent = r.latency_ms != null ? fmtLatency(r.latency_ms) : '—';
    outCaseId.textContent = r.image_id || r.case_id || '—';

    interpretation.textContent = r.interpretation || '';

    for (const cls of ['NORMAL', 'PNEUMONIA']) {
      const p = probs ? (probs[cls] || 0) : 0;
      $('probVal_' + cls).textContent = formatPct(p);
      $('probFill_' + cls).style.width = (p * 100).toFixed(1) + '%';
    }

    const name = r.patient_name || '';
    pNameLine.textContent = name || 'Unnamed patient';
    pMetaLine.textContent = [r.patient_mrn && 'MRN ' + r.patient_mrn, r.patient_sex, r.scan_date].filter(Boolean).join(' · ');
    patientLine.hidden = false;

    metaTime.textContent = new Date().toLocaleString();
    metaSaved.textContent = 'Record ' + (r.case_id || r.image_id || '').toUpperCase();

    if (r.case_id) {
      caseTag.hidden = false;
      caseTag.textContent = 'CASE ' + r.case_id.toUpperCase();
    }
  }

  async function analyze() {
    if (!selectedFile) return;
    hideError();
    analyzeBtn.disabled = true;
    spinner.hidden = false;
    btnLabel.textContent = 'Analyzing…';

    const fd = new FormData();
    fd.append('image', selectedFile);
    fd.append('model', modelSelect.value);
    fd.append('patient_name', patientName.value.trim());
    fd.append('patient_mrn', patientMrn.value.trim());
    fd.append('patient_sex', patientSex.value);
    fd.append('scan_date', scanDate.value);

    try {
      const res = await fetch('/api/predict', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Analysis failed.');
      currentResult = data;
      currentView = 'overlay';
      renderResult(data);
      updateView();
    } catch (err) {
      showError(err.message);
      resultEmpty.hidden = true;
    } finally {
      spinner.hidden = true;
      btnLabel.textContent = 'Analyze X-ray';
      analyzeBtn.disabled = false;
    }
  }

  let allRecords = [];

  function recordRow(r) {
    const card = document.createElement('div');
    card.className = 'rec-card';

    const thumb = document.createElement('img');
    thumb.className = 'rec-thumb';
    thumb.alt = '';
    thumb.src = r.image_url || r.image_path || '';
    thumb.onerror = () => { thumb.style.visibility = 'hidden'; };

    const info = document.createElement('div');
    info.className = 'rec-info';
    const nameLine = document.createElement('div');
    nameLine.className = 'rec-name';
    const name = document.createElement('span');
    name.textContent = r.patient_name || 'Unnamed patient';
    const dx = document.createElement('span');
    dx.className = 'rec-dx ' + (r.diagnosis === 'PNEUMONIA' ? 'pneumonia' : 'normal');
    dx.textContent = r.diagnosis;
    dx.title = r.diagnosis;
    nameLine.append(name, dx);
    const sub = document.createElement('div');
    sub.className = 'rec-sub';
    const reported = (r.reported_at || '').replace('T', ' ').slice(0, 16);
    sub.textContent = [r.patient_mrn && 'MRN ' + r.patient_mrn, reported].filter(Boolean).join(' · ')
      + ' · ' + Math.round((r.confidence || 0) * 100) + '% conf';
    info.append(nameLine, sub);

    const actions = document.createElement('div');
    actions.className = 'rec-actions';
    const viewBtn = document.createElement('button');
    viewBtn.className = 'view-rec-btn';
    viewBtn.title = 'Open';
    viewBtn.innerHTML = '<i data-icon="eye"></i>';
    viewBtn.addEventListener('click', () => openRecord(r.case_id));
    const delBtn = document.createElement('button');
    delBtn.className = 'del-rec-btn';
    delBtn.title = 'Delete';
    delBtn.innerHTML = '<i data-icon="trash-2"></i>';
    delBtn.addEventListener('click', () => deleteRecord(r.case_id));
    actions.append(viewBtn, delBtn);

    card.append(thumb, info, actions);
    return card;
  }

  function renderRecords() {
    recordsList.textContent = '';
    const q = recordSearch.value.trim().toLowerCase();
    const rows = (q ? allRecords.filter((r) => (r.patient_name || '').toLowerCase().includes(q)) : allRecords);
    recordCount.textContent = rows.length ? rows.length + ' assessment' + (rows.length === 1 ? '' : 's') : 'No records';
    if (!rows.length) {
      recordsList.append(recordsEmpty);
      recordsEmpty.hidden = false;
      return;
    }
    recordsEmpty.hidden = true;
    rows.forEach((r) => recordsList.append(recordRow(r)));
    hydrateIcons(recordsList);
  }

  async function openRecords() {
    recordsOverlay.hidden = false;
    recordSearch.value = '';
    try {
      const res = await fetch('/api/records');
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Could not load records.');
      allRecords = data.records || [];
      renderRecords();
    } catch (err) {
      allRecords = [];
      recordCount.textContent = err.message;
      recordsList.textContent = '';
    }
  }

  async function openRecord(caseId) {
    try {
      const res = await fetch('/api/records/' + caseId);
      const rec = await res.json();
      if (!res.ok) throw new Error(rec.error || 'Could not open record.');
      recordsOverlay.hidden = true;

      patientName.value = rec.patient_name || '';
      patientMrn.value = rec.patient_mrn || '';
      patientSex.value = rec.patient_sex || '';
      scanDate.value = rec.scan_date || '';

      const structured = {
        ...rec,
        image_url: rec.image_url || rec.image_path || '',
        overlay_url: rec.overlay_url || rec.overlay_path || '',
        heatmap_url: rec.heatmap_url || rec.heatmap_path || '',
      };
      currentResult = structured;
      currentView = 'overlay';
      updateView();
      renderResult(structured);
    } catch (err) {
      alert(err.message);
    }
  }

  async function deleteRecord(caseId) {
    if (!confirm('Delete this saved assessment?')) return;
    try {
      const res = await fetch('/api/records/' + caseId, { method: 'DELETE' });
      allRecords = allRecords.filter((r) => r.case_id !== caseId);
      renderRecords();
    } catch {
      alert('Could not delete record.');
    }
  }

  function closeRecordsOverlay() { recordsOverlay.hidden = true; }

  function printReport() {
    const r = currentResult || {};
    printDate.textContent = new Date().toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
    });
    printCaseId.textContent = (r.image_id || r.case_id || 'pending').toString().toUpperCase();
    window.print();
  }

  function showStorageForm() {
    storageInput.value = storagePath.textContent === '…' ? '' : storagePath.textContent;
    storageMsg.textContent = '';
    storageMsg.className = 'storage-msg';
    storageForm.hidden = false;
    storageInput.focus();
  }

  function setStoragePath(dir) {
    storagePath.textContent = dir;
    storagePath.title = dir;
  }

  async function loadSettings() {
    try {
      const res = await fetch('/api/settings');
      const data = await res.json();
      if (res.ok && data.data_dir) setStoragePath(data.data_dir);
    } catch {}
  }

  async function persistStorage(payload) {
    storageMsg.textContent = 'Saving…';
    storageMsg.className = 'storage-msg';
    try {
      const res = await fetch('/api/settings/storage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Could not update storage.');
      setStoragePath(data.data_dir);
      storageForm.hidden = true;
      storageMsg.textContent = 'Records storage updated.';
      storageMsg.className = 'storage-msg ok';
    } catch (err) {
      storageMsg.textContent = err.message;
      storageMsg.className = 'storage-msg err';
    }
  }
  stage.addEventListener('click', (e) => { if (!selectedFile) fileInput.click(); });
  stage.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
  });
  fileInput.addEventListener('change', () => selectFile(fileInput.files[0]));
  removeBtn.addEventListener('click', (e) => { e.stopPropagation(); clearSelection(); });
  image.addEventListener('click', (e) => { e.stopPropagation(); });
  analyzeBtn.addEventListener('click', analyze);
  modelSelect.addEventListener('change', setModelNote);

  viewBtns.forEach((btn) => btn.addEventListener('click', (e) => {
    e.stopPropagation();
    currentView = btn.dataset.view;
    updateView();
  }));

  printBtn.addEventListener('click', printReport);

  recordsBtn.addEventListener('click', openRecords);
  closeRecords.addEventListener('click', closeRecordsOverlay);
  recordsOverlay.addEventListener('click', (e) => { if (e.target === recordsOverlay) closeRecordsOverlay(); });
  recordSearch.addEventListener('input', renderRecords);

  storageSet.addEventListener('click', showStorageForm);
  storageCancel.addEventListener('click', () => { storageForm.hidden = true; });
  storageReset.addEventListener('click', () => persistStorage({ default: true }));
  storageForm.addEventListener('submit', (e) => {
    e.preventDefault();
    persistStorage({ data_dir: storageInput.value.trim() });
  });

  ['dragenter', 'dragover'].forEach((ev) =>
    stage.addEventListener(ev, (e) => { e.preventDefault(); stage.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((ev) =>
    stage.addEventListener(ev, (e) => { e.preventDefault(); stage.classList.remove('dragover'); }));
  stage.addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeRecordsOverlay();
  });

  setModelNote();
  loadSettings();
  hydrateIcons();
  modelStatus.classList.add('ready');
  modelStatus.textContent = MODELS.length + ' model' + (MODELS.length === 1 ? '' : 's') + ' ready';
})();