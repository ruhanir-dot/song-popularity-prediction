<script>
  const KEY_LABELS = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B']

  const DEFAULTS = {
    danceability: 0.5, energy: 0.5, loudness: -10, speechiness: 0.05,
    acousticness: 0.3, instrumentalness: 0, liveness: 0.15, valence: 0.5,
    tempo: 120, duration_ms: 210000, time_signature: 4, explicit: 0, key: 0, mode: 1,
  }

  let feat = $state({ ...DEFAULTS })
  let probability = $state(null)
  let isHit = $state(null)
  let loading = $state(false)
  let error = $state(null)

  const PRESETS = [
    { name: "Save Your Tears — The Weeknd", danceability: 0.68, energy: 0.826, loudness: -5.487, speechiness: 0.0309, acousticness: 0.0212, instrumentalness: 0.000012, liveness: 0.543, valence: 0.644, tempo: 118.051, duration_ms: 215627, time_signature: 4, explicit: 1, key: 0, mode: 1 },
    { name: "Blinding Lights — The Weeknd", danceability: 0.514, energy: 0.73, loudness: -5.934, speechiness: 0.0598, acousticness: 0.00146, instrumentalness: 0.0000954, liveness: 0.0897, valence: 0.334, tempo: 171.005, duration_ms: 200040, time_signature: 4, explicit: 0, key: 1, mode: 1 },
    { name: "The Business — Tiësto", danceability: 0.798, energy: 0.62, loudness: -7.079, speechiness: 0.232, acousticness: 0.414, instrumentalness: 0.0192, liveness: 0.112, valence: 0.235, tempo: 120.031, duration_ms: 164000, time_signature: 4, explicit: 0, key: 8, mode: 0 },
    { name: "Bandido — Myke Towers, Juhn", danceability: 0.713, energy: 0.617, loudness: -4.637, speechiness: 0.0887, acousticness: 0.122, instrumentalness: 0.0, liveness: 0.0962, valence: 0.682, tempo: 168.021, duration_ms: 232853, time_signature: 4, explicit: 0, key: 8, mode: 1 },
    { name: "WITHOUT YOU — The Kid LAROI", danceability: 0.662, energy: 0.413, loudness: -7.357, speechiness: 0.0299, acousticness: 0.213, instrumentalness: 0.0, liveness: 0.134, valence: 0.467, tempo: 93.005, duration_ms: 161385, time_signature: 4, explicit: 1, key: 0, mode: 1 },
    { name: "LA NOCHE DE ANOCHE — Bad Bunny, ROSALÍA", danceability: 0.856, energy: 0.618, loudness: -4.892, speechiness: 0.286, acousticness: 0.0303, instrumentalness: 0.0, liveness: 0.0866, valence: 0.391, tempo: 81.993, duration_ms: 203201, time_signature: 4, explicit: 0, key: 7, mode: 1 },
    { name: "Good Days — SZA", danceability: 0.436, energy: 0.655, loudness: -8.37, speechiness: 0.0583, acousticness: 0.499, instrumentalness: 0.0000081, liveness: 0.688, valence: 0.412, tempo: 121.002, duration_ms: 279204, time_signature: 4, explicit: 1, key: 1, mode: 0 },
    { name: "positions — Ariana Grande", danceability: 0.737, energy: 0.802, loudness: -4.771, speechiness: 0.0878, acousticness: 0.468, instrumentalness: 0.0, liveness: 0.0931, valence: 0.682, tempo: 144.015, duration_ms: 172325, time_signature: 4, explicit: 1, key: 0, mode: 1 },
    { name: "Hecha Pa' Mi — Boza", danceability: 0.725, energy: 0.756, loudness: -5.013, speechiness: 0.0572, acousticness: 0.362, instrumentalness: 0.000685, liveness: 0.103, valence: 0.828, tempo: 100.07, duration_ms: 186133, time_signature: 4, explicit: 0, key: 4, mode: 1 },
    { name: "Paradise — MEDUZA, Dermot Kennedy", danceability: 0.632, energy: 0.595, loudness: -7.644, speechiness: 0.0401, acousticness: 0.0689, instrumentalness: 0.0, liveness: 0.209, valence: 0.435, tempo: 124.114, duration_ms: 167903, time_signature: 4, explicit: 0, key: 8, mode: 0 },
    { name: "DÁKITI — Bad Bunny, Jhay Cortez", danceability: 0.731, energy: 0.573, loudness: -10.059, speechiness: 0.0544, acousticness: 0.401, instrumentalness: 0.0000522, liveness: 0.113, valence: 0.145, tempo: 109.928, duration_ms: 205090, time_signature: 4, explicit: 1, key: 4, mode: 0 },
    { name: "Head & Heart — Joel Corry, MNEK", danceability: 0.734, energy: 0.874, loudness: -3.158, speechiness: 0.0662, acousticness: 0.168, instrumentalness: 0.0000114, liveness: 0.0489, valence: 0.905, tempo: 122.953, duration_ms: 166028, time_signature: 4, explicit: 0, key: 8, mode: 1 },
    { name: "Dynamite — BTS", danceability: 0.746, energy: 0.765, loudness: -4.41, speechiness: 0.0993, acousticness: 0.0112, instrumentalness: 0.0, liveness: 0.0936, valence: 0.737, tempo: 114.044, duration_ms: 199054, time_signature: 4, explicit: 0, key: 6, mode: 0 },
    { name: "What You Know Bout Love — Pop Smoke", danceability: 0.709, energy: 0.548, loudness: -8.493, speechiness: 0.353, acousticness: 0.65, instrumentalness: 0.00000159, liveness: 0.133, valence: 0.543, tempo: 83.995, duration_ms: 160000, time_signature: 4, explicit: 1, key: 10, mode: 1 },
    { name: "BICHOTA — KAROL G", danceability: 0.863, energy: 0.666, loudness: -4.158, speechiness: 0.152, acousticness: 0.212, instrumentalness: 0.000493, liveness: 0.103, valence: 0.838, tempo: 163.908, duration_ms: 178947, time_signature: 4, explicit: 1, key: 1, mode: 0 },
    { name: "34+35 — Ariana Grande", danceability: 0.83, energy: 0.585, loudness: -6.476, speechiness: 0.094, acousticness: 0.237, instrumentalness: 0.0, liveness: 0.248, valence: 0.485, tempo: 109.978, duration_ms: 173711, time_signature: 4, explicit: 1, key: 0, mode: 1 },
  ]

  function loadPreset(idx) {
    if (idx === '') return
    const { name, ...values } = PRESETS[idx]
    feat = { ...values }
    probability = null; isHit = null
  }

  const SLIDERS = [
    { label: 'Danceability',      key: 'danceability',      min: 0,     max: 1,      step: 0.01 },
    { label: 'Energy',            key: 'energy',            min: 0,     max: 1,      step: 0.01 },
    { label: 'Loudness (dB)',     key: 'loudness',          min: -60,   max: 0,      step: 0.5  },
    { label: 'Speechiness',      key: 'speechiness',       min: 0,     max: 1,      step: 0.01 },
    { label: 'Acousticness',     key: 'acousticness',      min: 0,     max: 1,      step: 0.01 },
    { label: 'Instrumentalness', key: 'instrumentalness',  min: 0,     max: 1,      step: 0.01 },
    { label: 'Liveness',         key: 'liveness',          min: 0,     max: 1,      step: 0.01 },
    { label: 'Valence',          key: 'valence',           min: 0,     max: 1,      step: 0.01 },
    { label: 'Tempo (BPM)',      key: 'tempo',             min: 50,    max: 220,    step: 1    },
    { label: 'Duration (ms)',    key: 'duration_ms',       min: 30000, max: 600000, step: 1000 },
    { label: 'Time Signature',   key: 'time_signature',    min: 1,     max: 7,      step: 1    },
  ]

  function setVal(k, v, s) {
    const n = Number(v)
    if (isNaN(n)) return
    feat[k] = Math.min(s.max, Math.max(s.min, n))
  }

  async function predict() {
    loading = true
    error = null
    try {
      const res = await fetch('/predict_single', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feat)
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      probability = data.probability
      isHit = data.is_hit
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  function gaugeColor(p) {
    if (p < 0.33) return '#f85149'
    if (p < 0.66) return '#d29922'
    return '#1db954'
  }
</script>

<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
    <h2>🎛️ Tune Your Track</h2>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
      <span style="color: #8b949e; font-size: 0.85rem;">Example:</span>
      <select onchange={(e) => loadPreset(e.target.value)} style="max-width: 220px;">
        <option value="">— Select a track —</option>
        {#each PRESETS as p, i}
          <option value={i}>{p.name}</option>
        {/each}
      </select>
    </div>
  </div>

  <div class="grid">
    {#each SLIDERS as s}
      <div class="slider-group">
        <div class="slider-header">
          <span class="slider-label">{s.label}</span>
          <input
            class="num-input"
            type="number"
            min={s.min}
            max={s.max}
            step={s.step}
            value={feat[s.key]}
            onchange={(e) => setVal(s.key, e.target.value, s)}
          />
        </div>
        <input type="range" min={s.min} max={s.max} step={s.step}
          value={feat[s.key]}
          oninput={(e) => setVal(s.key, e.target.value, s)}
        />
      </div>
    {/each}

    <div class="slider-group">
      <label>Explicit:
        <select bind:value={feat.explicit}>
          <option value={0}>No</option>
          <option value={1}>Yes</option>
        </select>
      </label>
    </div>
    <div class="slider-group">
      <label>Key:
        <select bind:value={feat.key}>
          {#each KEY_LABELS as k, i}
            <option value={i}>{k}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="slider-group">
      <label>Mode:
        <select bind:value={feat.mode}>
          <option value={0}>Minor</option>
          <option value={1}>Major</option>
        </select>
      </label>
    </div>
  </div>

  <div style="text-align: center; margin-top: 1.25rem;">
    <button class="primary" onclick={predict} disabled={loading} style="padding: 0.7rem 2.5rem; font-size: 1rem;">
      {loading ? 'Predicting...' : 'Predict Hit'}
    </button>
  </div>
</div>

{#if error}
  <div class="card" style="text-align: center; color: #f85149;">{error}</div>
{/if}

{#if probability !== null}
  <div class="card" style="text-align: center;">
    <div class="gauge" style="--color: {gaugeColor(probability)}">
      <span class="gauge-value">{Math.round(probability * 100)}%</span>
    </div>
    <p style="margin-top: 0.5rem; font-size: 1.2rem;">
      {#if isHit}
        <span style="color: #1db954;">🔥 Potential Hit!</span>
      {:else}
        <span style="color: #f85149;">Not likely a hit</span>
      {/if}
    </p>
  </div>
{/if}

<style>
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1.5rem; }
  .slider-group label { display: flex; justify-content: space-between; font-size: 0.85rem; color: #8b949e; margin-bottom: 0.2rem; }
  .slider-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem; }
  .slider-label { font-size: 0.85rem; color: #8b949e; }
  .num-input {
    width: 90px;
    background: #0d1117;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 0.15rem 0.4rem;
    font-size: 0.85rem;
    text-align: right;
    -moz-appearance: textfield;
  }
  .num-input:focus { outline: none; border-color: #1db954; }
  .gauge { width: 120px; height: 120px; border-radius: 50%; border: 6px solid var(--color); display: flex; align-items: center; justify-content: center; margin: 0 auto; transition: border-color 0.3s; }
  .gauge-value { font-size: 2rem; font-weight: 700; color: var(--color); }
  h2 { font-size: 1.1rem; }
</style>
