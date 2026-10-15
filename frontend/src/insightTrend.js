export const TREND_SERIES = [
  { key: "cited_answer", label: "有引用回答", color: "#17675f" },
  { key: "no_evidence", label: "依据不足", color: "#92550b" },
  { key: "failure", label: "失败", color: "#b73f3d" },
  { key: "unknown_outcome", label: "结果未知", color: "#64748b" },
];

export function utcDayLabel(value) {
  const match = String(value ?? "").match(/^(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : "";
}

export function trendChartData(points) {
  const rows = Array.isArray(points) ? points : [];
  return {
    labels: rows.map((row) => utcDayLabel(row?.bucket_start)),
    datasets: TREND_SERIES.map((series) => ({
      label: series.label,
      backgroundColor: series.color,
      data: rows.map((row) => {
        const value = Number(row?.[series.key]);
        return Number.isFinite(value) ? value : 0;
      }),
    })),
  };
}

export function trendCaption(points) {
  const totals = trendChartData(points).datasets.map((set) => set.data.reduce((sum, value) => sum + value, 0));
  const [cited, missing, failed, unknown] = totals;
  return `学生提交按 UTC 日计数：有引用回答 ${cited}，依据不足 ${missing}，失败 ${failed}，结果未知 ${unknown}。没有事件的日期为 0。`;
}
