<script>
  import HitMaker from "./lib/HitMaker.svelte"
  import BatchPredict from "./lib/BatchPredict.svelte"

  let tab = $state("hitmaker")
</script>

<h1>Spotify Hit Predictor</h1>

<div class="tabs">
  <button class:active={tab === "hitmaker"} onclick={() => tab = "hitmaker"}>Single Prediction</button>
  <button class:active={tab === "batch"} onclick={() => tab = "batch"}>Batch Analysis</button>
</div>

{#if tab === "hitmaker"}
  <HitMaker />
{:else if tab === "batch"}
  <BatchPredict />
{/if}
