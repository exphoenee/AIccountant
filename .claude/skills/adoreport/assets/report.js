(function () {
  "use strict";
  var DATA = JSON.parse(document.getElementById("report-data").textContent);
  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function cv(n) { return getComputedStyle(root).getPropertyValue(n).trim(); }
  var nf = new Intl.NumberFormat("hu-HU", { maximumFractionDigits: 0 });
  function ft(v) { return nf.format(Math.round(v)).replace(/\s/g, " ") + " Ft"; }
  function short(v) {
    var a = Math.abs(v);
    if (a >= 1e6) return (v / 1e6).toLocaleString("hu-HU", { maximumFractionDigits: 2 }) + " M";
    if (a >= 1e3) return nf.format(v / 1e3) + " e";
    return nf.format(v);
  }
  function alpha(hex, a) {
    var h = hex.replace("#", "");
    if (h.length === 3) h = h.split("").map(function (c) { return c + c; }).join("");
    var n = parseInt(h, 16);
    return "rgba(" + (n >> 16) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }
  function colors() {
    return { ink: cv("--c-ink"), income: cv("--c-income"), slate: cv("--c-slate"), muted: cv("--muted"),
             line: cv("--line"), bg: cv("--bg"), surface: cv("--surface"), accent: cv("--accent") };
  }
  function vgrad(color, top, bottom) {
    return function (ctx) {
      var ca = ctx.chart.chartArea;
      if (!ca) return color;
      var g = ctx.chart.ctx.createLinearGradient(0, ca.top, 0, ca.bottom);
      g.addColorStop(0, alpha(color, top)); g.addColorStop(1, alpha(color, bottom));
      return g;
    };
  }
  var charts = [];
  // a jelmagyarázat alatt hely marad: a legfelső Y-tengelycímke ne érjen bele (a Chart.js a legendet közvetlenül a területre teszi)
  var legendSpacing = { id: "legendSpacing", beforeInit: function (chart) {
    var fit = chart.legend && chart.legend.fit;
    if (!fit) return;
    chart.legend.fit = function () { fit.bind(chart.legend)(); if (chart.legend.options.display) chart.legend.height += 22; };
  } };
  function make(id, cfg) {
    var el = document.getElementById(id);
    if (!el) return;
    cfg.plugins = (cfg.plugins || []).concat([legendSpacing]);
    charts.push(new Chart(el, cfg));
  }
  function base(c, extra) {
    var o = {
      responsive: true, maintainAspectRatio: false,
      animation: reduce ? false : { duration: 1100, easing: "easeOutQuart" },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false, position: "top", align: "start",
                  labels: { usePointStyle: true, pointStyle: "rectRounded", boxWidth: 8, boxHeight: 8, padding: 18, color: c.muted } },
        tooltip: { backgroundColor: c.ink, titleColor: c.bg, bodyColor: c.bg, padding: 12, cornerRadius: 10, boxPadding: 6,
                   displayColors: true, usePointStyle: true,
                   callbacks: { label: function (i) { return i.parsed.y == null && i.parsed.x == null ? "" :
                     " " + i.dataset.label + ": " + ft(i.parsed.y != null && i.chart.options.indexAxis !== "y" ? i.parsed.y : i.parsed.x); } } }
      },
      scales: {
        x: { grid: { display: false }, border: { color: c.line }, ticks: { color: c.muted } },
        y: { beginAtZero: true, grid: { color: c.line }, border: { display: false },
             ticks: { color: c.muted, maxTicksLimit: 6, callback: function (v) { return short(v); } } }
      }
    };
    return merge(o, extra || {});
  }
  function merge(a, b) {
    Object.keys(b).forEach(function (k) {
      if (b[k] && typeof b[k] === "object" && !Array.isArray(b[k]) && a[k] && typeof a[k] === "object") merge(a[k], b[k]);
      else a[k] = b[k];
    });
    return a;
  }
  var RB = { topLeft: 8, topRight: 8 };

  function build() {
    var c = colors();
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.font.size = 13;
    Chart.defaults.color = c.muted;

    if (DATA.income) {
      make("ch-income", { type: "bar", data: { labels: DATA.months, datasets: [
        { type: "bar", label: "Havi nettó bevétel", data: DATA.income, backgroundColor: vgrad(c.income, 1, 0.45), hoverBackgroundColor: c.income,
          borderRadius: RB, borderSkipped: false, maxBarThickness: 44, yAxisID: "y", order: 2 },
        { type: "line", label: "Göngyölt bevétel", data: DATA.cum, borderColor: c.ink, backgroundColor: c.ink, tension: 0.35,
          borderWidth: 2.5, pointRadius: 3, pointHoverRadius: 6, yAxisID: "y1", spanGaps: false, order: 1 },
        { type: "line", label: DATA.thr_label, data: DATA.months.map(function () { return DATA.thr; }), borderColor: c.slate,
          borderDash: [6, 6], borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 0, yAxisID: "y1", order: 0 }
      ] }, options: base(c, { plugins: { legend: { display: true } }, scales: {
        y: { title: { display: true, text: "Havi", color: c.muted } },
        y1: { position: "right", beginAtZero: true, grid: { display: false }, border: { display: false },
              title: { display: true, text: "Göngyölt", color: c.muted },
              ticks: { color: c.muted, maxTicksLimit: 6, callback: function (v) { return short(v); } } } } }) });
    }
    if (DATA.spark) {
      make("ch-spark", { type: "line", data: { labels: DATA.spark.labels, datasets: [{ data: DATA.spark.values, borderColor: c.income,
        borderWidth: 2, tension: 0.4, pointRadius: 0, fill: true, backgroundColor: vgrad(c.income, 0.32, 0) }] },
        options: { responsive: true, maintainAspectRatio: false, animation: reduce ? false : { duration: 1400, easing: "easeOutQuart" },
                   events: [], plugins: { legend: { display: false }, tooltip: { enabled: false } },
                   scales: { x: { display: false }, y: { display: false, beginAtZero: true } }, layout: { padding: 0 } } });
    }
    if (DATA.clients && DATA.clients.length) {
      var pal = [c.income, c.ink, c.slate, alpha(c.income, 0.55), alpha(c.ink, 0.5), alpha(c.slate, 0.55)];
      make("ch-clients", { type: "doughnut", data: { labels: DATA.clients.map(function (x) { return x.name; }),
        datasets: [{ data: DATA.clients.map(function (x) { return x.value; }), backgroundColor: DATA.clients.map(function (_, i) { return pal[i % pal.length]; }),
          borderColor: c.bg, borderWidth: 3, hoverOffset: 8 }] },
        options: { responsive: true, maintainAspectRatio: false, cutout: "70%", animation: reduce ? false : { duration: 1200, easing: "easeOutQuart" },
                   plugins: { legend: { display: false }, tooltip: { backgroundColor: c.ink, titleColor: c.bg, bodyColor: c.bg, padding: 12, cornerRadius: 10,
                     callbacks: { label: function (i) { return " " + ft(i.parsed); } } } } } });
      document.querySelectorAll("[data-sw]").forEach(function (el) { el.style.background = pal[+el.getAttribute("data-sw") % pal.length]; });
    }
    (DATA.gauges || []).forEach(function (g, i) {
      var used = Math.min(g.ratio, 1);
      make("ch-gauge" + i, { type: "doughnut", data: { datasets: [{ data: [used, 1 - used],
        backgroundColor: [g.ratio > 1 ? c.ink : c.income, c.surface], borderWidth: 0, borderRadius: 8 }] },
        options: { responsive: true, maintainAspectRatio: false, rotation: -90, circumference: 180, cutout: "80%",
                   animation: reduce ? false : { duration: 1300, easing: "easeOutQuart" }, events: [],
                   plugins: { legend: { display: false }, tooltip: { enabled: false } } } });
    });
    if (DATA.exp && DATA.exp.months) {
      make("ch-exp", { type: "bar", data: { labels: DATA.months, datasets: [{ label: "Kiadás", data: DATA.exp.months,
        backgroundColor: vgrad(c.slate, 1, 0.5), borderRadius: RB, borderSkipped: false, maxBarThickness: 44 }] }, options: base(c) });
    }
    if (DATA.deemed) {
      make("ch-deemed", { type: "bar", data: { labels: ["Átalány-költség", "Rögzített kiadás"], datasets: [{ label: "Összeg",
        data: [DATA.deemed.deemed, DATA.deemed.recorded], backgroundColor: [c.slate, c.income], borderRadius: 8, borderSkipped: false, maxBarThickness: 36 }] },
        options: base(c, { indexAxis: "y", interaction: { mode: "nearest", intersect: true }, scales: {
          x: { beginAtZero: true, grid: { color: c.line }, border: { display: false }, ticks: { color: c.muted, maxTicksLimit: 5, callback: function (v) { return short(v); } } },
          y: { grid: { display: false }, ticks: { color: c.ink, callback: function (v) { return this.getLabelForValue(v); } } } } }) });
    }
    if (DATA.quarters) {
      var qd = [{ label: "SZJA előleg", data: DATA.quarters.szja, backgroundColor: c.ink }];
      if (DATA.quarters.tbj) {
        qd.push({ label: "TBJ", data: DATA.quarters.tbj, backgroundColor: c.income });
        qd.push({ label: "SZOCHO", data: DATA.quarters.szocho, backgroundColor: c.slate });
      }
      qd.forEach(function (d) { d.borderRadius = RB; d.borderSkipped = false; d.maxBarThickness = 40; });
      make("ch-quarters", { type: "bar", data: { labels: DATA.quarters.labels, datasets: qd }, options: base(c, { plugins: { legend: { display: true } } }) });
    }
    if (DATA.cmp) {
      make("ch-cmp", { type: "bar", data: { labels: DATA.cmp.labels, datasets: [
        { label: "Számított göngyölt kötelezettség", data: DATA.cmp.computed, backgroundColor: c.ink, borderRadius: RB, borderSkipped: false, maxBarThickness: 40 },
        { label: "NAV adószámlán befizetve", data: DATA.cmp.paid, backgroundColor: c.income, borderRadius: RB, borderSkipped: false, maxBarThickness: 40 }] },
        options: base(c, { plugins: { legend: { display: true } } }) });
    }
    if (DATA.pay) {
      var cols = [c.ink, c.income, c.slate];
      make("ch-pay", { type: "bar", data: { labels: DATA.months, datasets: DATA.pay.series.map(function (s, i) {
        return { label: s.name, data: s.values, backgroundColor: cols[i], borderRadius: i === DATA.pay.series.length - 1 ? RB : 0, borderSkipped: false, maxBarThickness: 44 }; }) },
        options: base(c, { plugins: { legend: { display: true } }, scales: { x: { stacked: true }, y: { stacked: true } } }) });
    }
  }
  function rebuild() { charts.forEach(function (ch) { ch.destroy(); }); charts = []; build(); }

  // mobil menü: a gomb a nyitott/zárt állapotot is kimondja; Esc, linkkattintás és szélesítés zár
  var nav = document.querySelector(".nav"), mt = document.getElementById("menu-toggle");
  function setMenu(open) {
    if (!nav || !mt) return;
    if (open) { nav.setAttribute("data-open", ""); document.body.setAttribute("data-menu-open", ""); }
    else { nav.removeAttribute("data-open"); document.body.removeAttribute("data-menu-open"); }
    mt.setAttribute("aria-expanded", open ? "true" : "false");
    mt.setAttribute("aria-label", open ? "Menü bezárása" : "Menü megnyitása");
  }
  if (mt) {
    mt.addEventListener("click", function () { setMenu(!nav.hasAttribute("data-open")); });
    document.querySelectorAll("#nav-menu a").forEach(function (a) { a.addEventListener("click", function () { setMenu(false); }); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setMenu(false); });
    window.addEventListener("resize", function () { if (window.innerWidth > 960) setMenu(false); });
  }

  // téma-kapcsoló: egyetlen gomb, világos <-> sötét; a választás a localStorage-ban van, a kezdő téma a böngészőből jön (head script)
  var tb = document.getElementById("theme-toggle");
  if (tb) tb.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("adoreport-theme", next); } catch (e) {}
    rebuild();
  });

  // egyetlen számláló a hero mutatón: a végén mindig a script által kiszámolt pontos szöveg áll
  document.querySelectorAll("[data-count]").forEach(function (el) {
    var target = parseFloat(el.getAttribute("data-count")), final = el.getAttribute("data-final");
    if (reduce || !isFinite(target)) { el.textContent = final; return; }
    var t0 = null;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min((ts - t0) / 1300, 1), e = 1 - Math.pow(1 - p, 4);
      el.textContent = p < 1 ? ft(target * e) : final;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });

  build();
})();
