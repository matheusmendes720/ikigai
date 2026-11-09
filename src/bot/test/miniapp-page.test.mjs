/**
 * THE PAGE: where the credential comes from.
 *
 * The Mini App is a PUBLISHED surface: the page ships in the image and the
 * owner reads his session through it. Its server half is gated by the
 * Python suite — that is the CHECK. This is the other half: the page has to
 * FIND the credential at all.
 *
 * It used not to. The Telegram client opens a Mini App with the payload in
 * the URL FRAGMENT (`#tgWebAppData=…`), and the official SDK
 * (telegram-web-app.js) is what parses that fragment into
 * `Telegram.WebApp.initData` — the SDK is what CREATES that object. The
 * page read `window.Telegram.WebApp` and never loaded the SDK, so on a real
 * client the object was absent, the credential went out EMPTY, and the
 * server refused with "the initData carries no hash" — a refusal that reads
 * like a wrong signature and is really a missing one.
 *
 * These tests run the PAGE'S OWN function. A copy of it in the test would
 * test the copy, and the copy would be right while the page stayed broken.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const PAGE_PATH = join(HERE, "..", "miniapp", "index.html");
const PAGE = readFileSync(PAGE_PATH, "utf8");

/**
 * Pull one function out of the page, by its braces, and hand it back as
 * source. The strings and the comments are skipped so a brace inside them
 * cannot end the function early.
 */
function extractFunction(source, name) {
  const marker = `function ${name}(`;
  const at = source.indexOf(marker);
  assert.notEqual(at, -1, `the page must still define ${name}()`);
  const open = source.indexOf("{", at);
  let depth = 0;
  let quote = null;
  for (let i = open; i < source.length; i += 1) {
    const c = source[i];
    if (quote) {
      if (c === "\\") { i += 1; continue; }
      if (c === quote) { quote = null; }
      continue;
    }
    if (c === '"' || c === "'" || c === "`") { quote = c; continue; }
    if (c === "{") { depth += 1; continue; }
    if (c === "}") {
      depth -= 1;
      if (depth === 0) { return source.slice(at, i + 1); }
    }
  }
  throw new Error(`the function ${name}() is never closed`);
}

/** Run the page's own reader against a fragment. */
function readFragment(hash) {
  const source = [
    extractFunction(PAGE, "urlSafeDecode"),
    extractFunction(PAGE, "fragmentInitData"),
  ].join("\n");
  const read = new Function(
    "window",
    `${source}\nreturn fragmentInitData();`,
  );
  return read({ location: { hash } });
}

test("the page finds the payload the client puts in the fragment", () => {
  const payload =
    "auth_date=1794250000&query_id=AAHdF6IQAAAAAN0XohDhrOrc&" +
    "user=%7B%22id%22%3A9138296750%2C%22first_name%22%3A%22Matheus%22%7D&" +
    "hash=2f8a1c9d4b6e7f0a1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b";
  const hash = `#tgWebAppData=${encodeURIComponent(payload)}&tgWebAppVersion=6.9`;
  assert.equal(readFragment(hash), payload);
});

test("the page reads the fragment the way the SDK reads it", () => {
  // The SDK's urlSafeDecode turns '+' into a space; Python's parse_qsl — the
  // server's decoder — does the same. If the page decoded it differently,
  // the two ways of finding the credential would disagree and the signature
  // Telegram computed would never match.
  assert.equal(readFragment("#tgWebAppData=a+b"), "a b");
  assert.equal(readFragment("#tgWebAppData=a%2Bb"), "a+b");
  assert.equal(readFragment("#tgWebAppData=a%20b"), "a b");
});

test("the payload is the only thing taken from the fragment", () => {
  const hash =
    "#tgWebAppData=auth_date%3D1%26hash%3Dabc&tgWebAppVersion=6.9&" +
    "tgWebAppPlatform=windows&themeParams=%7B%7D";
  assert.equal(readFragment(hash), "auth_date=1&hash=abc");
});

test("a fragment without a payload yields nothing", () => {
  assert.equal(readFragment(""), "");
  assert.equal(readFragment("#"), "");
  assert.equal(readFragment("#tgWebAppVersion=6.9"), "");
  assert.equal(readFragment("#tgWebAppData="), "");
});

test("the page loads the official SDK", () => {
  // The SDK is what creates `Telegram.WebApp`; the client does not have to.
  // It is loaded WITHOUT async/defer and BEFORE the page's own script, so it
  // has run by the time the page reads the bridge.
  const sdk = PAGE.indexOf("https://telegram.org/js/telegram-web-app.js");
  assert.notEqual(sdk, -1, "the page must load the official SDK");
  const own = PAGE.indexOf("(function () {");
  assert.ok(sdk < own, "the SDK must come before the page's own script");
  assert.ok(
    !/telegram-web-app\.js"[^>]*\b(async|defer)\b/.test(PAGE),
    "the SDK must not be async or deferred: the page reads the bridge at once",
  );
});

test("the page does not capture the credential once, at load", () => {
  // A credential captured when the script ran can only ever be right at the
  // moment the script ran. The bridge is a network fetch: it may land later,
  // and the page has to find the payload at the moment it asks for it.
  assert.ok(
    !/\bvar\s+INIT_DATA\b/.test(PAGE),
    "the credential must not be captured into a constant at load",
  );
  assert.ok(
    !/\bvar\s+START_PARAM\b/.test(PAGE),
    "the start param must not be captured into a constant at load",
  );
  assert.ok(
    /init_data:\s*initData\(\)/.test(PAGE),
    "the request must carry the credential read at that moment",
  );
});

test("the refusal names the cause instead of blaming the signature", () => {
  // "Not authenticated" is not a diagnosis. A missing credential and a
  // refused one arrive as the same 401, and dressing the second as the
  // first sends the hunt after the signature instead of after the payload.
  assert.ok(
    PAGE.includes("O Telegram não entregou o initData"),
    "the page must say when there was no credential at all",
  );
});
