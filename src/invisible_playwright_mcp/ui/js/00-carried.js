// What this page keeps in the browser, and how a value saved under the
// previous name gets carried across.
//
// The keys were prefixed with the product's old brand until 2026-09-23. The
// origin does not change with a rename: the interface is served from the same
// 127.0.0.1 before and after, so those entries are still in the browser of
// everybody who used it. Reading only the new key does not move them, it just
// stops finding them, and one of the three holds an UNSENT DRAFT - text
// somebody typed and has not sent.
//
// So the read moves it: new key first, retired key second, and when the second
// is what answered the value is written under the new name and the old entry
// removed. Once per value, by construction, because after the move there is
// nothing left under the old name to find.
//
// One place knows both prefixes and the move. Three files keep a key each, and
// a rule spelled out in three of them is a rule that gets changed in one.

const STORE = 'invisible-playwright-mcp.';
const STORE_WAS = 'aihawk.';

// The value under `key`, or under the name it replaced, or null.
//
// Every access is wrapped: localStorage throws rather than returning null in a
// browser where site data is blocked, and a page that cannot remember a pane
// width still has to draw.
function carried(key) {
  try {
    const mine = localStorage.getItem(key);
    if (mine !== null) { return mine; }
    const was = STORE_WAS + key.slice(STORE.length);
    const old = localStorage.getItem(was);
    if (old === null) { return null; }
    localStorage.setItem(key, old);
    localStorage.removeItem(was);
    return old;
  } catch (err) {
    return null;
  }
}
