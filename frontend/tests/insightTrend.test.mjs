import assert from "node:assert/strict";
import test from "node:test";
import { trendCaption, trendChartData, utcDayLabel } from "../src/insightTrend.js";

test("trend labels stay on the UTC calendar day", () => {
  const data = trendChartData([
    {
      bucket_start: "2026-10-15T23:30:00+00:00",
      cited_answer: 1,
      no_evidence: 2,
      failure: 3,
      unknown_outcome: 4,
    },
  ]);
  assert.deepEqual(data.labels, ["2026-10-15"]);
  assert.deepEqual(data.datasets.map((series) => series.label), ["有引用回答", "依据不足", "失败", "结果未知"]);
  assert.deepEqual(data.datasets.map((series) => series.data[0]), [1, 2, 3, 4]);
  assert.equal(utcDayLabel("2026-10-16T00:00:00Z"), "2026-10-16");
  assert.match(trendCaption([{ bucket_start: "2026-10-15T00:00:00Z", cited_answer: 2, no_evidence: 0, failure: 1, unknown_outcome: 0 }]), /失败 1/);
});

test("missing trend points do not invent a local day", () => {
  assert.deepEqual(trendChartData(null), {
    labels: [],
    datasets: trendChartData([]).datasets,
  });
});
