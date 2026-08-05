const DEFAULT_PATH_HINT = "c:\\Users\\user\\Downloads\\Prompt Indikator Bali_NEW.xlsx";

const PERIOD_PATTERNS = [
  /^(19|20)\d{2}$/,
  /^triwulan\s*[ivx\d]+[\s\-/]*(19|20)?\d{2,4}$/i,
  /^q[1-4][\s\-/]*(19|20)?\d{2,4}$/i,
  /^(19|20)\d{2}[\s\-/]*q[1-4]$/i,
  /^t[1-4][\s\-/]*(19|20)?\d{2,4}$/i,
  /^(19|20)\d{2}[\s\-/]*t[1-4]$/i,
  /^semester\s*[12][\s\-/]*(19|20)?\d{2,4}$/i,
];

const LABEL_KEYWORDS = [
  "indikator", "variabel", "subject", "keterangan", "uraian",
  "deskripsi", "nama", "lapangan usaha", "komponen", "sektor",
];

const ECONOMIC_CONTEXT = [
  {
    keys: ["pariwisata", "akomodasi", "makan minum"],
    other: ["pertanian"],
    text:
      "Sektor pariwisata dan pertanian sering bergerak berlawanan. Saat kunjungan wisata meningkat, tenaga kerja dan investasi cenderung bergeser ke jasa wisata sehingga pertumbuhan pertanian relatif melambat.",
  },
  {
    keys: ["ekspor"],
    other: ["impor"],
    text:
      "Ekspor yang meningkat biasanya didukung impor bahan baku. Namun jika pertumbuhan ekspor didorong permintaan domestik, impor bisa tertekan sementara.",
  },
  {
    keys: ["konsumsi pemerintah", "pk-p", "belanja pemerintah"],
    other: ["konsumsi rumah tangga", "krt"],
    text:
      "Belanja pemerintah yang naik dapat menstimulus ekonomi jangka pendek, tetapi jika sumber daya terbatas, konsumsi rumah tangga bisa melambat (efek crowding-out).",
  },
  {
    keys: ["konstruksi"],
    other: ["real estat", "properti"],
    text:
      "Boom konstruksi sering diikuti normalisasi real estat karena pipeline proyek habis atau oversupply properti wisata.",
  },
  {
    keys: ["transportasi", "logistik"],
    other: ["pariwisata", "akomodasi"],
    text:
      "Transportasi dan pariwisata cenderung bergerak searah: lebih banyak wisatawan meningkatkan permintaan penerbangan dan transport darat.",
  },
  {
    keys: ["jasa keuangan", "keuangan"],
    other: ["konstruksi", "investasi"],
    text:
      "Kredit investasi mendorong konstruksi. Jika jasa keuangan melambat akibat ketatnya kredit, pertumbuhan konstruksi ikut tertekan.",
  },
];

let workbook = null;
let parsedSheets = {};
let trendChart = null;

function isPeriod(name) {
  const text = String(name || "").trim();
  if (!text || text.toLowerCase().startsWith("unnamed")) return false;
  return PERIOD_PATTERNS.some((p) => p.test(text));
}

function toNumber(value) {
  if (value == null || value === "") return null;
  if (typeof value === "number") return value;
  let text = String(value).trim().replace("%", "").replace(",", ".");
  text = text.replace(/[^\d.\-]/g, "");
  const n = parseFloat(text);
  return Number.isFinite(n) ? n : null;
}

function detectHeaderRow(rows) {
  let best = 0;
  let bestScore = -1;
  for (let i = 0; i < Math.min(rows.length, 25); i++) {
    const row = rows[i] || [];
    const nonNull = row.filter((x) => x != null && String(x).trim() !== "").length;
    const periodHits = row.filter((x) => isPeriod(x)).length;
    const labelHits = row.filter((x) =>
      LABEL_KEYWORDS.some((k) => String(x || "").toLowerCase().includes(k))
    ).length;
    const score = nonNull + periodHits * 3 + labelHits * 2;
    if (score > bestScore) {
      bestScore = score;
      best = i;
    }
  }
  return best;
}

function pickLabelCol(headers) {
  for (const h of headers) {
    const lower = String(h).toLowerCase();
    if (LABEL_KEYWORDS.some((k) => lower.includes(k))) return h;
  }
  return headers[0];
}

function periodSortKey(period) {
  const text = String(period).toLowerCase();
  const yearMatch = text.match(/(19|20)\d{2}/);
  const year = yearMatch ? parseInt(yearMatch[0], 10) : 0;
  let quarter = 0;
  if (/triwulan\s*iv|q4|t4|\s4/.test(text)) quarter = 4;
  else if (/triwulan\s*iii|q3|t3|\s3/.test(text)) quarter = 3;
  else if (/triwulan\s*ii|q2|t2|\s2/.test(text)) quarter = 2;
  else if (/triwulan\s*i[^i]|q1|t1|\s1/.test(text)) quarter = 1;
  return [year, quarter, text];
}

function comparePeriod(a, b) {
  const ka = periodSortKey(a);
  const kb = periodSortKey(b);
  for (let i = 0; i < 3; i++) {
    if (ka[i] < kb[i]) return -1;
    if (ka[i] > kb[i]) return 1;
  }
  return 0;
}

function parseSheet(sheetName) {
  const sheet = workbook.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: null });
  if (!rows.length) return null;

  const headerRow = detectHeaderRow(rows);
  const headers = (rows[headerRow] || []).map((h, idx) =>
    h == null || String(h).trim() === "" ? `Unnamed_${idx}` : String(h).trim()
  );
  const periodCols = headers.filter(isPeriod);
  if (!periodCols.length) return null;

  const labelCol = pickLabelCol(headers);
  const labelIdx = headers.indexOf(labelCol);
  const data = [];

  for (let r = headerRow + 1; r < rows.length; r++) {
    const row = rows[r] || [];
    const subject = row[labelIdx];
    if (!subject || String(subject).trim() === "") continue;
    const entry = { subyek: String(subject).trim(), values: {} };
    for (const col of periodCols) {
      const idx = headers.indexOf(col);
      const val = toNumber(row[idx]);
      if (val != null) entry.values[col] = val;
    }
    if (Object.keys(entry.values).length) data.push(entry);
  }

  const periods = [...new Set(data.flatMap((d) => Object.keys(d.values)))].sort(comparePeriod);
  return { sheetName, labelCol, periods, data };
}

function parseWorkbook() {
  parsedSheets = {};
  for (const name of workbook.SheetNames) {
    const parsed = parseSheet(name);
    if (parsed && parsed.data.length) parsedSheets[name] = parsed;
  }
}

function pearson(x, y) {
  const n = x.length;
  if (n < 3) return NaN;
  const mx = x.reduce((a, b) => a + b, 0) / n;
  const my = y.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let dx = 0;
  let dy = 0;
  for (let i = 0; i < n; i++) {
    const vx = x[i] - mx;
    const vy = y[i] - my;
    num += vx * vy;
    dx += vx * vx;
    dy += vy * vy;
  }
  const den = Math.sqrt(dx * dy);
  return den === 0 ? NaN : num / den;
}

function analyzeTrend(values) {
  const keys = Object.keys(values).sort(comparePeriod);
  if (!keys.length) return { direction: "stabil", latest: 0, change: null, avg: 0, keys };
  const nums = keys.map((k) => values[k]);
  const latest = nums[nums.length - 1];
  const prev = nums.length >= 2 ? nums[nums.length - 2] : null;
  const change = prev == null ? null : latest - prev;
  const recent = nums.slice(-4);
  const avg = recent.reduce((a, b) => a + b, 0) / recent.length;
  let direction = "stabil";
  if (change != null) {
    if (change > 0.15) direction = "naik";
    else if (change < -0.15) direction = "turun";
  }
  return { direction, latest, change, avg, keys };
}

function relationshipLabel(corr) {
  if (corr <= -0.45) return "berbanding terbalik";
  if (corr >= 0.45) return "searah";
  return "lemah";
}

function findContext(a, b) {
  const sa = a.toLowerCase();
  const sb = b.toLowerCase();
  for (const item of ECONOMIC_CONTEXT) {
    const matchA = item.keys.some((k) => sa.includes(k));
    const matchB = item.other.some((k) => sb.includes(k));
    const matchA2 = item.keys.some((k) => sb.includes(k));
    const matchB2 = item.other.some((k) => sa.includes(k));
    if ((matchA && matchB) || (matchA2 && matchB2)) return item.text;
  }
  return null;
}

function genericExplanation(selected, other, selTrend, othTrend, corr, rel) {
  if (rel === "berbanding terbalik") {
    if (selTrend === "naik" && othTrend === "turun") {
      return `Ketika <strong>${selected}</strong> tren <strong>naik</strong>, <strong>${other}</strong> cenderung <strong>turun</strong> (korelasi ${corr.toFixed(2)}). Pola ini sering muncul karena pergeseran sumber daya antarsektor atau efek musiman di ekonomi Bali.`;
    }
    if (selTrend === "turun" && othTrend === "naik") {
      return `Penurunan <strong>${selected}</strong> beriringan kenaikan <strong>${other}</strong> (korelasi ${corr.toFixed(2)}). Sektor lain mengisi gap permintaan saat sektor utama melemah.`;
    }
    return `<strong>${selected}</strong> dan <strong>${other}</strong> bergerak berbanding terbalik (korelasi ${corr.toFixed(2)}).`;
  }
  if (rel === "searah") {
    return `<strong>${selected}</strong> dan <strong>${other}</strong> bergerak searah (korelasi ${corr.toFixed(2)}), dipengaruhi faktor makro yang sama seperti siklus pariwisata atau kebijakan fiskal.`;
  }
  return `Hubungan <strong>${selected}</strong> dengan <strong>${other}</strong> relatif lemah (korelasi ${corr.toFixed(2)}).`;
}

function generateInsights(sheetData, selectedSubject) {
  const selected = sheetData.data.find((d) => d.subyek === selectedSubject);
  if (!selected) return { trend: null, insights: [] };

  const selTrend = analyzeTrend(selected.values);
  const insights = [];

  for (const other of sheetData.data) {
    if (other.subyek === selectedSubject) continue;
    const periods = selTrend.keys.filter((p) => other.values[p] != null);
    if (periods.length < 4) continue;
    const xs = periods.map((p) => selected.values[p]);
    const ys = periods.map((p) => other.values[p]);
    const corr = pearson(xs, ys);
    if (!Number.isFinite(corr)) continue;

    const othTrend = analyzeTrend(other.values);
    const rel = relationshipLabel(corr);
    const context = findContext(selectedSubject, other.subyek);
    const explanation =
      context ||
      genericExplanation(
        selectedSubject,
        other.subyek,
        selTrend.direction,
        othTrend.direction,
        corr,
        rel
      );

    let rank = Math.abs(corr);
    if (
      selTrend.direction === "naik" &&
      othTrend.direction === "turun" &&
      corr < 0
    )
      rank += 2;
    if (
      selTrend.direction === "turun" &&
      othTrend.direction === "naik" &&
      corr < 0
    )
      rank += 2;

    insights.push({
      other: other.subyek,
      corr,
      rel,
      othTrend: othTrend.direction,
      explanation,
      rank,
    });
  }

  insights.sort((a, b) => b.rank - a.rank);
  return { trend: selTrend, insights: insights.slice(0, 6) };
}

function trendTag(dir) {
  const cls = dir === "naik" ? "up" : dir === "turun" ? "down" : "flat";
  const arrow = dir === "naik" ? "↑" : dir === "turun" ? "↓" : "→";
  return `<span class="tag ${cls}">${dir} ${arrow}</span>`;
}

function renderDashboard() {
  const sheetName = document.getElementById("sheetSelect").value;
  const subject = document.getElementById("subjectSelect").value;
  const sheetData = parsedSheets[sheetName];
  if (!sheetData || !subject) return;

  const selected = sheetData.data.find((d) => d.subyek === subject);
  const { trend, insights } = generateInsights(sheetData, subject);

  document.getElementById("metricsSection").classList.remove("hidden");
  document.getElementById("chartsSection").classList.remove("hidden");
  document.getElementById("insightsSection").classList.remove("hidden");

  document.getElementById("mLatest").textContent = `${trend.latest.toFixed(2)}%`;
  document.getElementById("mTrend").innerHTML = trendTag(trend.direction);
  document.getElementById("mAvg").textContent = `${trend.avg.toFixed(2)}%`;
  document.getElementById("mPeriods").textContent = trend.keys.length;

  const labels = trend.keys;
  const values = labels.map((k) => selected.values[k]);

  if (trendChart) trendChart.destroy();
  const ctx = document.getElementById("trendChart");
  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: subject,
          data: values,
          borderColor: "#38bdf8",
          backgroundColor: "rgba(56,189,248,0.15)",
          fill: true,
          tension: 0.25,
          pointRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: {
        x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,0.15)" } },
        y: {
          ticks: { color: "#94a3b8", callback: (v) => `${v}%` },
          grid: { color: "rgba(148,163,184,0.15)" },
        },
      },
    },
  });

  const thead = document.querySelector("#dataTable thead");
  const tbody = document.querySelector("#dataTable tbody");
  thead.innerHTML = "<tr><th>Periode</th><th>Pertumbuhan (%)</th></tr>";
  tbody.innerHTML = labels
    .map(
      (p) =>
        `<tr><td>${p}</td><td>${selected.values[p].toFixed(2)}</td></tr>`
    )
    .join("");

  const changeText =
    trend.change != null
      ? ` Perubahan terakhir: ${trend.change >= 0 ? "+" : ""}${trend.change.toFixed(2)} poin.`
      : "";
  document.getElementById("summaryInsight").innerHTML = `
    <div class="insight">
      <div class="insight-title">${subject} ${trendTag(trend.direction)}</div>
      Nilai terakhir <strong>${trend.latest.toFixed(2)}%</strong>.${changeText}
      Rata-rata 4 periode terakhir: <strong>${trend.avg.toFixed(2)}%</strong>.
    </div>`;

  const list = document.getElementById("insightsList");
  if (!insights.length) {
    list.innerHTML = `<p class="status">Belum cukup data untuk insight korelasi.</p>`;
    return;
  }

  list.innerHTML = insights
    .map((item) => {
      const cls =
        item.rel === "berbanding terbalik"
          ? "inverse"
          : item.rel === "searah"
          ? "positive"
          : "";
      const icon =
        item.rel === "berbanding terbalik"
          ? "↔️"
          : item.rel === "searah"
          ? "↗️"
          : "〰️";
      return `
        <div class="insight ${cls}">
          <div class="insight-title">${icon} ${subject} ↔ ${item.other}
            — ${item.rel} (r = ${item.corr.toFixed(2)}) | tren lain: ${trendTag(item.othTrend)}
          </div>
          <div>${item.explanation}</div>
        </div>`;
    })
    .join("");
}

function populateSelectors() {
  const sheetSelect = document.getElementById("sheetSelect");
  const subjectSelect = document.getElementById("subjectSelect");
  const sheetNames = Object.keys(parsedSheets);

  sheetSelect.innerHTML = sheetNames.map((s) => `<option value="${s}">${s}</option>`).join("");
  sheetSelect.disabled = false;

  function updateSubjects() {
    const sheet = parsedSheets[sheetSelect.value];
    subjectSelect.innerHTML = sheet.data
      .map((d) => `<option value="${d.subyek}">${d.subyek}</option>`)
      .join("");
    subjectSelect.disabled = false;
    renderDashboard();
  }

  sheetSelect.onchange = updateSubjects;
  subjectSelect.onchange = renderDashboard;
  updateSubjects();
}

function loadArrayBuffer(buffer, sourceLabel) {
  workbook = XLSX.read(buffer, { type: "array" });
  parseWorkbook();
  const count = Object.keys(parsedSheets).length;
  document.getElementById("status").textContent =
    `Berhasil memuat ${sourceLabel}: ${workbook.SheetNames.length} sheet, ${count} sheet valid.`;
  populateSelectors();
}

document.getElementById("fileInput").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => loadArrayBuffer(ev.target.result, file.name);
  reader.readAsArrayBuffer(file);
});

document.getElementById("loadDefaultBtn").addEventListener("click", async () => {
  document.getElementById("status").textContent =
    "Browser tidak bisa akses file lokal otomatis. Silakan upload file Excel via input di atas.";
  alert(
    "Karena keamanan browser, file di Downloads tidak bisa dibaca otomatis.\n\n" +
      "Silakan klik 'Choose File' dan pilih:\n" +
      DEFAULT_PATH_HINT
  );
});
