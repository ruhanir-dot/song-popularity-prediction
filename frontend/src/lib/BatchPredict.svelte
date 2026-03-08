<script>
  import { tick, onMount } from 'svelte'
  import Chart from 'chart.js/auto'

  let results = $state([])
  let loading = $state(false)
  let error = $state(null)
  let dragover = $state(false)
  let page = $state(0)
  let isValidation = $state(false)
  let hasMetrics = $state(false)
  let metricsLoading = $state(false)
  const PAGE_SIZE = 20

  let rocCanvas = $state()
  let fiCanvas = $state()
  let rocChart = null
  let fiChart = null

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
    try {
      const res = await fetch(url, { method: 'POST', body })
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
    form.append('file', file)
    fetchPredictions('/predict_batch', form, false)
  }

  function runValidation() {
    fetchPredictions('/run_validation', null, true)
  }

  async function loadMetrics() {
    metricsLoading = true
    try {
      const res = await fetch('/get_metrics')
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      metricsLoading = false

      await tick()

      if (rocChart) rocChart.destroy()
      if (fiChart) fiChart.destroy()

      rocChart = new Chart(rocCanvas, {
        type: 'line',
        data: {
          labels: data.roc.fpr.map(v => v.toFixed(2)),
          datasets: [
            {
              label: `ROC Curve (AUC = ${data.roc.auc})`,
              data: data.roc.tpr,
              borderColor: '#1db954',
              backgroundColor: 'rgba(29,185,84,0.1)',
              fill: true,
              pointRadius: 0,
              tension: 0.1,
            },
            {
              label: 'Random',
              data: data.roc.fpr,
              borderColor: '#30363d',
              borderDash: [5, 5],
              pointRadius: 0,
            }
          ]
        },
        options: {
          responsive: true,
          plugins: { title: { display: true, text: 'ROC Curve', color: '#e6edf3' }, legend: { labels: { color: '#8b949e' } } },
          scales: {
            x: { title: { display: true, text: 'False Positive Rate', color: '#8b949e' }, ticks: { color: '#8b949e', maxTicksLimit: 10 }, grid: { color: '#21262d' } },
            y: { title: { display: true, text: 'True Positive Rate', color: '#8b949e' }, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
          }
        }
      })

      const fi = Object.entries(data.feature_importance).sort((a, b) => b[1] - a[1]).slice(0, 15)
      fiChart = new Chart(fiCanvas, {
        type: 'bar',
        data: {
          labels: fi.map(([n]) => n),
          datasets: [{
            label: 'Permutation Importance',
            data: fi.map(([, v]) => v),
            backgroundColor: '#1db954',
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          plugins: { title: { display: true, text: 'Feature Importance (Top 15)', color: '#e6edf3' }, legend: { display: false } },
          scales: {
            x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
            y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } },
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

  let correct = $derived(isValidation ? results.filter(r => r.is_hit === r.actual_hit).length : 0)
</script>

<div class="card" style="display: flex; gap: 1rem; align-items: stretch;">
  <button type="button" class="drop-zone" style="flex: 1;" class:dragover
    ondragover={(e) => { e.preventDefault(); dragover = true }}
    ondragleave={() => dragover = false}
    ondrop={onDrop}
    onclick={() => document.getElementById('csv-input').click()}>
    <p>Drop a CSV file here or click to upload</p>
    <input id="csv-input" type="file" accept=".csv" style="display:none" onchange={onFileInput} />
  </button>
  <div style="display: flex; flex-direction: column; justify-content: center; gap: 0.5rem; min-width: 180px;">
    <span style="color: #8b949e; font-size: 0.8rem; text-align: center;">or use the built-in set</span>
    <button class="primary" onclick={runValidation} disabled={loading}>
      Run Validation Demo
    </button>
    <span style="color: #8b949e; font-size: 0.75rem; text-align: center;">12,096 songs from 2020</span>
  </div>
</div>

{#if error}
  <div class="card" style="text-align: center; color: #f85149;">{error}</div>
{/if}

{#if loading}
  <div class="spinner"></div>
{/if}

{#if results.length > 0}
  <div class="card">
    <p style="color: #8b949e; margin-bottom: 0.75rem;">
      {results.length} tracks predicted
      {#if isValidation}
        — Accuracy: {(correct / results.length * 100).toFixed(1)}% ({correct}/{results.length} correct)
      {/if}
    </p>
    <table>
      <thead>
        <tr>
          <th>Track</th>
          {#if isValidation}<th>Artists</th><th>Actual</th>{/if}
          <th>Predicted</th>
          <th>Probability</th>
          {#if isValidation}<th></th>{/if}
        </tr>
      </thead>
      <tbody>
        {#each pageResults as r}
          <tr>
            <td>{r.name}</td>
            {#if isValidation}<td style="color: #8b949e; font-size: 0.85rem;">{r.artists}</td>{/if}
            {#if isValidation}
              <td style="color: {r.actual_hit ? '#1db954' : '#f85149'}">{r.actual_hit ? 'Hit' : 'No'}</td>
            {/if}
            <td style="color: {r.is_hit ? '#1db954' : '#f85149'}">{r.is_hit ? 'Hit' : 'No'}</td>
            <td>{Math.round(r.probability * 100)}%</td>
            {#if isValidation}
              <td>{r.is_hit === r.actual_hit ? '✓' : '✗'}</td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if totalPages > 1}
      <div class="pagination">
        <button disabled={page === 0} onclick={() => page--}>Prev</button>
        <span style="padding: 0.3rem; color: #8b949e;">{page + 1} / {totalPages}</span>
        <button disabled={page >= totalPages - 1} onclick={() => page++}>Next</button>
      </div>
    {/if}
  </div>
{/if}

{#if hasMetrics}
  {#if metricsLoading}
    <div class="spinner"></div>
  {:else}
    <div class="card">
      <canvas bind:this={rocCanvas}></canvas>
    </div>
    <div class="card">
      <canvas bind:this={fiCanvas}></canvas>
    </div>
  {/if}
{/if}
