import { test } from "node:test";
import assert from "node:assert/strict";
import { shouldShowHelpOnStart, HELP_VERSION, HELP_SECTIONS } from "../../site/js/help.js";

test("help opens automatically on first visit and after help content version changes", () => {
  assert.equal(shouldShowHelpOnStart(null), true);
  assert.equal(shouldShowHelpOnStart("0"), true);
  assert.equal(shouldShowHelpOnStart(String(HELP_VERSION)), false);
});

test("help covers every map feature", () => {
  const text = HELP_SECTIONS.map((s) => s.title + s.body).join(" ");
  for (const word of ["반경", "🚶", "🏃", "🚲", "⛰️", "💪", "🪑", "🌳", "🚻", "🏪", "📏", "📝", "◎", "🏁", "네이버", "10km"]) {
    assert.ok(text.includes(word), word);
  }
});
