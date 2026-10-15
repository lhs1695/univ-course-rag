<template>
  <div class="trend-chart">
    <canvas ref="canvas" role="img" :aria-label="caption"></canvas>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { BarController, BarElement, CategoryScale, Chart, Legend, LinearScale, Tooltip } from "chart.js";
import { trendCaption, trendChartData } from "../insightTrend";

Chart.register(BarController, BarElement, CategoryScale, LinearScale, Legend, Tooltip);

const props = defineProps({
  points: { type: Array, default: () => [] },
});
const canvas = ref(null);
const caption = computed(() => trendCaption(props.points));
let chart;

function render() {
  if (!canvas.value) return;
  const data = trendChartData(props.points);
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { stacked: true, ticks: { autoSkip: true, maxRotation: 0 } },
      y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } },
    },
    plugins: {
      legend: { position: "bottom" },
      tooltip: { mode: "index", intersect: false },
    },
  };
  if (chart) {
    chart.data = data;
    chart.update();
    return;
  }
  chart = new Chart(canvas.value, { type: "bar", data, options });
}

onMounted(render);
watch(() => props.points, render);
onBeforeUnmount(() => {
  chart?.destroy();
  chart = null;
});
</script>

<style scoped>
.trend-chart {
  height: 280px;
  margin-top: 8px;
}
</style>
