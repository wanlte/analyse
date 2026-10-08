import { answerParts } from "./answer.js";

export function boardSummary(board) {
  const parts = answerParts(board.answer || "");
  return {
    range: board.data_date || "",
    line: parts.conclusion || "",
  };
}

export function boardLink(id, origin) {
  return `${origin}/?board=${id}`;
}
