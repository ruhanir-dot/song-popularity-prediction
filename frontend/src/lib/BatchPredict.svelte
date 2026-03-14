<script>
  import { tick, onMount } from "svelte"
  import Chart from "chart.js/auto"

  let results = $state([])
  let loading = $state(false)
  let error = $state(null)
  let dragover = $state(false)
  let page = $state(0)
  let isValidation = $state(false)
  let hasMetrics = $state(false)
  let metricsLoading = $state(false)
  const PAGE_SIZE = 20

  const GRUV = {
    green: "#b8bb26",
    red: "#fb4934",
    bg2: "#3c3836",
    fg0: "#ebdbb2",
    fg1: "#a89984",
    fg2: "#928374",
    bg1: "#32302f"
  }

  let rocCanvas = $state()
  let fiCanvas = $state()
  let rocChart = null
  let fiChart = null
  let holdoutMetrics = $state(null)

  onMount(() => {
    return () => {
      if (rocChart) rocChart.destroy()
      if (fiChart) fiChart.destroy()
    }
  })

  async function fetchPredictions(url, body, validation) {
    loading = true
    error = null
    results = []
    isValidation = validation
    hasMetrics = false
    holdoutMetrics = null
    try {
      const res = await fetch(url, { method: "POST", body })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      results = data.results
      page = 0
      if (data.has_metrics) {
        hasMetrics = true
        loadMetrics()
      }
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  function upload(file) {
    if (!file) return
    const form = new FormData()
    form.append("file", file)
    fetchPredictions("/predict_batch", form, false)
  }

  function runValidation() {
    fetchPredictions("/run_validation", null, true)
  }

  const KEY_LABELS = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"]

  async function loadMetrics() {
    metricsLoading = true
    try {
      const res = await fetch("/get_metrics")
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      metricsLoading = false
      holdoutMetrics = {
        threshold: data.threshold,
        gb: data.gb_holdout,
      }

      await tick()

      if (rocChart) rocChart.destroy()
      if (fiChart) fiChart.destroy()

      const chartFont = { family: "JetBrains Mono", size: 10 }

      rocChart = new Chart(rocCanvas, {
        type: "line",
        data: {
          labels: data.roc.fpr.map(v => v.toFixed(2)),
          datasets: [
            {
              label: `GB ROC (AUC = ${data.roc.auc})`,
              data: data.roc.tpr,
              borderColor: GRUV.green,
              backgroundColor: "rgba(184, 187, 38, 0.1)",
              fill: true,
              pointRadius: 0,
              tension: 0.1,
            },
            {
              label: "Random",
              data: data.roc.fpr,
              borderColor: GRUV.fg2,
              borderDash: [5, 5],
              pointRadius: 0,
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            title: { display: true, text: "ROC PERFORMANCE", color: GRUV.fg0, font: { family: "Outfit", size: 14, weight: 700 } },
            legend: { labels: { color: GRUV.fg2, font: chartFont } }
          },
          scales: {
            x: {
              title: { display: true, text: "FALSE POSITIVE RATE", color: GRUV.fg2, font: chartFont },
              ticks: { color: GRUV.fg2, font: chartFont, maxTicksLimit: 10 },
              grid: { color: GRUV.bg2 }
            },
            y: {
              title: { display: true, text: "TRUE POSITIVE RATE", color: GRUV.fg2, font: chartFont },
              ticks: { color: GRUV.fg2, font: chartFont },
              grid: { color: GRUV.bg2 }
            },
          }
        }
      })

      const fi = Object.entries(data.feature_importance)
        .map(([name, val]) => {
          let label = name.toUpperCase()
          if (label.startsWith("KEY_")) {
            const keyIdx = parseInt(label.split("_")[1])
            if (!isNaN(keyIdx)) label = `KEY: ${KEY_LABELS[keyIdx]}`
          } else if (label === "MODE_0") {
            label = "MODE: MINOR"
          } else if (label === "MODE_1") {
            label = "MODE: MAJOR"
          }
          return [label, val]
        })
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15)

      fiChart = new Chart(fiCanvas, {
        type: "bar",
        data: {
          labels: fi.map(([n]) => n.toUpperCase()),
          datasets: [{
            label: "Importance",
            data: fi.map(([, v]) => v),
            backgroundColor: GRUV.green,
          }]
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            title: { display: true, text: "FEATURE IMPORTANCE", color: GRUV.fg0, font: { family: "Outfit", size: 14, weight: 700 } },
            legend: { display: false }
          },
          scales: {
            x: { ticks: { color: GRUV.fg2, font: chartFont }, grid: { color: GRUV.bg2 } },
            y: { 
              ticks: { 
                color: GRUV.fg2, 
                font: chartFont,
                autoSkip: false,
                padding: 10
              }, 
              grid: { color: "transparent" } 
            },
          }
        }
      })
    } catch (e) {
      error = e.message
      metricsLoading = false
    }
  }

  function onDrop(e) {
    e.preventDefault()
    dragover = false
    upload(e.dataTransfer.files[0])
  }

  function onFileInput(e) {
    upload(e.target.files[0])
  }

    let totalPages = $derived(Math.ceil(results.length / PAGE_SIZE))
  let pageResults = $derived(results.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE))
  let correctGb = $derived(isValidation ? results.filter(r => r.gb_is_hit === r.actual_hit).length : 0)
</script>

<div class="batch-header card">
  <button type="button" class="drop-zone" class:dragover
    ondragover={(e) => { e.preventDefault(); dragover = true }}
    ondragleave={() => dragover = false}
    ondrop={onDrop}
    onclick={() => document.getElementById("csv-input").click()}>
    <p>UPLOAD DATASET (CSV)</p>
    <input id="csv-input" type="file" accept=".csv" style="display:none" onchange={onFileInput} />
  </button>
  <div class="divider">
    <span>OR</span>
  </div>
  <div class="demo-actions">
    <button class="primary" onclick={runValidation} disabled={loading}>
      {loading ? "PROCESSING..." : "RUN VALIDATION"}
    </button>
    <span class="meta">12,096 tracks from 2020 archive</span>
  </div>
</div>

{#if error}
  <div class="card error-card">{error}</div>
{/if}

{#if loading}
  <div class="spinner"></div>
{/if}

  {#if results.length > 0}
  <div class="card">
    <div class="results-meta">
      <span class="count">{results.length} Tracks Analysed</span>
      {#if isValidation}
        <div class="accuracy-group">
          <span class="accuracy">Accuracy: {(correctGb / results.length * 100).toFixed(1)}%</span>
        </div>
      {/if}
    </div>
    <table>
      <thead>
        <tr>
          <th>Track Title</th>
          {#if isValidation}<th>Artists</th><th>Actual</th>{/if}
          <th>GB Pred</th>
          <th>GB Conf</th>
          {#if isValidation}<th>Status</th>{/if}
        </tr>
      </thead>
      <tbody class="mono">
        {#each pageResults as r}
          <tr>
            <td class="name">{r.name}</td>
            {#if isValidation}<td class="artists">{r.artists}</td>{/if}
            {#if isValidation}
              <td style="color: {r.actual_hit ? "var(--green)" : "var(--fg-2)"}">{r.actual_hit ? "HIT" : "LOW"}</td>
            {/if}
            <td style="color: {r.gb_is_hit ? "var(--green)" : "var(--red)"}">{r.gb_is_hit ? "HIT" : "LOW"}</td>
            <td>{Math.round(r.gb_probability * 100)}%</td>
            {#if isValidation}
              <td style="color: {r.gb_is_hit === r.actual_hit ? "var(--green)" : "var(--red)"}">
                {r.gb_is_hit === r.actual_hit ? "OK" : "MIS"}
              </td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if totalPages > 1}
      <div class="pagination">
        <button disabled={page === 0} onclick={() => page--}>PREV</button>
        <span class="page-info">{page + 1} / {totalPages}</span>
        <button disabled={page >= totalPages - 1} onclick={() => page++}>NEXT</button>
      </div>
    {/if}
  </div>
{/if}

{#if hasMetrics}
  {#if metricsLoading}
    <div class="spinner"></div>
  {:else}
    <div class="metrics-grid">
      <div class="metrics-column">
        <div class="card chart-card">
          <canvas bind:this={rocCanvas}></canvas>
        </div>

        {#if holdoutMetrics}
          <div class="card holdout-card">
            <h2 class="holdout-title">2020 Holdout Results <span class="threshold-tag">threshold = {holdoutMetrics.threshold}</span></h2>
            <div class="holdout-container">
              {#each [{ label: "Gradient Boosting", data: holdoutMetrics.gb, color: "var(--green)" }] as m}
                <div class="holdout-model">
                  <h3 class="model-name" style="color: {m.color}">{m.label}</h3>
                  <div class="summary-stats">
                    <div class="stat">
                      <span class="stat-label">Accuracy</span>
                      <span class="stat-value">{(m.data.accuracy * 100).toFixed(2)}%</span>
                    </div>
                    <div class="stat">
                      <span class="stat-label">ROC-AUC</span>
                      <span class="stat-value">{m.data.roc_auc.toFixed(4)}</span>
                    </div>
                  </div>
                  <table class="report-table">
                    <thead>
                      <tr>
                        <th></th>
                        <th>Prec</th>
                        <th>Rec</th>
                        <th>F1</th>
                        <th>Supp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each ["Not a Hit", "Hit", "macro avg"] as cls, i}
                        {@const r = m.data.report[cls]}
                        {@const label = i < 2 ? cls : cls.split(" ").map(w => w[0].toUpperCase() + w.slice(1)).join(" ")}
                        <tr class:report-divider={i === 2}>
                          <td class="cls-label">{label}</td>
                          <td>{r.precision.toFixed(2)}</td>
                          <td>{r.recall.toFixed(2)}</td>
                          <td>{r["f1-score"].toFixed(2)}</td>
                          <td>{r.support}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>

      <div class="metrics-column">
        <div class="card chart-card full-height">
          <canvas bind:this={fiCanvas}></canvas>
        </div>
      </div>
    </div>
  {/if}
{/if}

<style>
  .batch-header { display: flex; align-items: stretch; gap: 2rem; padding: 2.5rem; }
  .drop-zone { flex: 1; border-style: dashed; padding: 3rem; }
  .divider { display: flex; flex-direction: column; justify-content: center; align-items: center; }
  .divider span { font-family: "JetBrains Mono", monospace; font-size: 0.7rem; color: var(--fg-2); letter-spacing: 0.2em; }
  .demo-actions { display: flex; flex-direction: column; justify-content: center; gap: 1rem; min-width: 240px; }
  .demo-actions .meta { font-family: "JetBrains Mono", monospace; font-size: 0.65rem; color: var(--fg-2); text-transform: uppercase; letter-spacing: 0.05em; text-align: center; }
  .results-meta { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2rem; border-bottom: 1px solid var(--bg-2); padding-bottom: 1rem; }
  .results-meta .count { font-family: "Outfit", sans-serif; font-weight: 700; font-size: 1.1rem; }
  .accuracy-group { display: flex; gap: 1.5rem; }
  .results-meta .accuracy { font-family: "JetBrains Mono", monospace; font-size: 0.85rem; color: var(--green); text-transform: uppercase; }
  .mono { font-family: "JetBrains Mono", monospace; font-size: 0.85rem; }
  .name { color: var(--fg-0); font-family: "Instrument Sans", sans-serif; font-weight: 500; font-size: 0.95rem; }
  .artists { color: var(--fg-2); font-size: 0.75rem; }
  .error-card { text-align: center; color: var(--red); border-color: var(--red); }
  .page-info { font-family: "JetBrains Mono", monospace; font-size: 0.75rem; color: var(--fg-2); display: flex; align-items: center; }
  
  .metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1.5rem; align-items: stretch; }
  .metrics-column { display: flex; flex-direction: column; gap: 1.5rem; }
  
  .chart-card { padding: 1.5rem; height: 350px; }
  .full-height { height: 100%; min-height: 800px; }
  
  .holdout-card { flex: 1; padding: 1.5rem; }
  .holdout-title { font-size: 1.1rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--bg-2); padding-bottom: 0.75rem; display: flex; align-items: baseline; gap: 1rem; justify-content: center; }
  .threshold-tag { font-family: "JetBrains Mono", monospace; font-size: 0.7rem; color: var(--fg-2); text-transform: uppercase; letter-spacing: 0.05em; }
  .holdout-container { width: 100%; display: flex; justify-content: center; }
  .holdout-model { width: 100%; }
  .model-name { font-family: "JetBrains Mono", monospace; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; text-align: center; }
  .summary-stats { display: flex; gap: 2rem; margin-bottom: 1.25rem; justify-content: center; }
  .stat { display: flex; flex-direction: column; gap: 0.25rem; }
  .stat-label { font-family: "JetBrains Mono", monospace; font-size: 0.65rem; text-transform: uppercase; color: var(--fg-2); letter-spacing: 0.05em; }
  .stat-value { font-family: "Outfit", sans-serif; font-size: 1.4rem; font-weight: 800; color: var(--fg-0); }
  .report-table { width: 100%; border-collapse: collapse; font-family: "JetBrains Mono", monospace; font-size: 0.75rem; }
  .report-table th { font-size: 0.6rem; text-transform: uppercase; color: var(--fg-2); letter-spacing: 0.05em; padding: 0.4rem 0.6rem; text-align: right; border-bottom: 1px solid var(--bg-2); }
  .report-table th:first-child { text-align: left; }
  .report-table td { padding: 0.4rem 0.6rem; text-align: right; color: var(--fg-1); border-bottom: 1px solid var(--bg-2); }
  .report-table .cls-label { text-align: left; color: var(--fg-0); font-weight: 600; }
  .report-divider td { border-top: 2px solid var(--bg-2); }
</style>
