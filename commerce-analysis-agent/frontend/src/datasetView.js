export function contentLines(detail) {
  const files = detail && detail.files ? detail.files : {};
  return Object.entries(files).flatMap(([slot, file]) => {
    const columns = (file.columns || []).join("、");
    const head = `${slot} · ${file.row_count} 行 · ${columns}`;
    const rows = (file.preview || []).slice(0, 5).map((row) => JSON.stringify(row));
    return [head, ...rows];
  });
}
