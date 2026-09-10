
const $ = id => document.getElementById(id);
/* ---- markdown, and the gate lifts everything down to the end of `rich` ----
   These lines are the only ones in this file a JavaScript engine runs during
   the tests: `test_the_answer_pane_draws_markdown.py` cuts the region out and
   executes it against a DOM small enough to print. The markers exist so that
   cut is exact - moving them means moving what is under test. */
const el = (t,c,x) => { const e = document.createElement(t);
                        if(c) e.className = c; if(x != null) e.textContent = x; return e; };

/* Markdown to NODES, never to a string of HTML.
   The text arriving here was written by a model that has just read arbitrary
   web pages, so it is chosen by whoever wrote the last page it visited. Putting
   it through innerHTML is the documented road to exfiltration by injected
   image, and no amount of sanitising makes that road shorter than this one.
   So: the marks become elements, built by hand, and the text between them stays
   text. A `<script>` in the answer is still drawn as the characters of a
   script, because it never stops being a text node.
   Images are absent on purpose - they are the exfiltration vector itself, and
   an `<img>` fetches its source the instant it enters the document, with no
   click and no error needed. A link is drawn but never made clickable, and its
   destination is PRINTED rather than hidden behind words, so an injected
   address is legible instead of invisible. */
function inline(text, into){
  for(const part of text.split(/(\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*|!?\[[^\]\n]*\]\([^()\s]*\))/)){
    if(!part) continue;
    const two = part.length > 4 && part.startsWith('**') && part.endsWith('**');
    const tick = part.length > 2 && part.startsWith('`') && part.endsWith('`');
    const one = part.length > 2 && !two && part.startsWith('*') && part.endsWith('*');
    const link = /^!?\[([^\]\n]*)\]\(([^()\s]*)\)$/.exec(part);
    if(two)       into.appendChild(el('strong', null, part.slice(2, -2)));
    else if(tick) into.appendChild(el('code', null, part.slice(1, -1)));
    else if(one)  into.appendChild(el('em', null, part.slice(1, -1)));
    else if(link){ if(link[1]) into.appendChild(el('span','lk', link[1]));
                   if(link[2]) into.appendChild(el('span','href', link[2])); }
    else          into.appendChild(document.createTextNode(part));
  }
}

/* The block marks, which are most of what a model writes: it answers in
   headings and lists far more often than in the three inline marks this pane
   understood until now, and every one of them was drawn as its own characters -
   `## Roles` arrived on screen as a hash, a hash and a space. */
const HEAD   = /^(#{1,6})\s+(.*)$/;
const BULLET = /^(\s*)[-*+]\s+(.*)$/;
const NUMBER = /^(\s*)\d+[.)]\s+(.*)$/;
const QUOTE  = /^\s*>\s?(.*)$/;
const RULE   = /^\s*([-*_])\s*(?:\1\s*){2,}$/;
const CELLS  = /\|/;
const DASHES = /^[\s:|-]*-[\s:|-]*$/;

/* ⛔ A FLOOR ON THE RECURSION, because this text was written by a model
   that had just read arbitrary web pages. Measured against the extracted
   parser: 20,000 `>` on one line, or a list indented 10,000 levels, throws
   RangeError - and the throw does not land in the parser, it lands in the
   event handler, where it strands the step clock, skips the redraw and eats
   the queued instruction. Past this depth the marks are drawn as the text
   they are, which is what nesting that deep actually is. */
const DEEP = 24;
function blocks(text, into, depth){
  depth = depth || 0;
  const lines = text.split('\n');
  let i = 0;
  while(i < lines.length){
    const line = lines[i];
    if(!line.trim()){ i++; continue; }
    const head = HEAD.exec(line);
    if(head){
      /* `#` lands on h3: the page's own title is above this pane, and an answer
         that opened at h1 would outrank it in the document outline. */
      const h = el('h' + Math.min(head[1].length + 2, 6), 'md-h');
      inline(head[2], h); into.appendChild(h); i++; continue;
    }
    if(RULE.test(line)){ into.appendChild(el('hr','md-hr')); i++; continue; }
    if(QUOTE.test(line) && depth < DEEP){
      const held = [];
      while(i < lines.length && QUOTE.test(lines[i])) held.push(QUOTE.exec(lines[i++])[1]);
      const q = el('blockquote','md-q');
      blocks(held.join('\n'), q, depth + 1); /* a quote holds blocks like any other */
      into.appendChild(q); continue;
    }
    if(CELLS.test(line) && i + 1 < lines.length && DASHES.test(lines[i + 1])
       && lines[i + 1].includes('-')){ i = tableAt(lines, i, into); continue; }
    if((BULLET.test(line) || NUMBER.test(line)) && depth < DEEP){
      i = listAt(lines, i, into, depth); continue;
    }
    /* ⛔ THE FIRST LINE IS TAKEN WITHOUT ASKING, and that is what makes this
       loop finish. Every branch above consumes; this one is the floor, so if
       its condition ever excluded the line that got here the walker would sit
       on it forever building empty paragraphs - a hung tab, not a bad render.
       Measured while mutating the list branch away: the browser stops. */
    const held = [lines[i++]];
    while(i < lines.length && lines[i].trim() && !HEAD.test(lines[i])
          && !RULE.test(lines[i]) && !QUOTE.test(lines[i])
          && !BULLET.test(lines[i]) && !NUMBER.test(lines[i])) held.push(lines[i++]);
    const p = el('p','md-p');
    inline(held.join('\n'), p);
    into.appendChild(p);
  }
}

/* Both of these return the line to carry on from, so the walker above never has
   to guess how much they ate - a block parser that advances by one and hopes is
   how a list ends up inside itself. */
function listAt(lines, i, into, depth){
  const first = BULLET.exec(lines[i]) || NUMBER.exec(lines[i]);
  const base = first[1].length;
  const ordered = !BULLET.test(lines[i]);
  const box = el(ordered ? 'ol' : 'ul', 'md-l');
  let item = null;
  while(i < lines.length && lines[i].trim()){
    const mark = BULLET.exec(lines[i]) || NUMBER.exec(lines[i]);
    if(!mark){
      /* A line under an item and not marked is the rest of that item. */
      if(!item) break;
      item.appendChild(document.createTextNode('\n' + lines[i].trim()));
      i++; continue;
    }
    if(mark[1].length > base && (depth || 0) < DEEP){
      i = listAt(lines, i, item || box, (depth || 0) + 1); continue;
    }
    if(mark[1].length < base || !BULLET.test(lines[i]) !== ordered) break;
    item = el('li','md-i');
    inline(mark[2], item);
    box.appendChild(item);
    i++;
  }
  into.appendChild(box);
  return i;
}

function tableAt(lines, i, into){
  const cells = row => row.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|');
  const box = el('table','md-t');
  const head = el('tr','md-r');
  for(const c of cells(lines[i])) inline(c.trim(), head.appendChild(el('th')));
  box.appendChild(head);
  i += 2;                                   /* the header row and its dashes */
  while(i < lines.length && lines[i].trim() && CELLS.test(lines[i])){
    const tr = el('tr','md-r');
    for(const c of cells(lines[i])) inline(c.trim(), tr.appendChild(el('td')));
    box.appendChild(tr); i++;
  }
  into.appendChild(box);
  return i;
}

function rich(text){
  const frag = document.createDocumentFragment();
  /* An odd number of fences means the last block never closed, which is what a
     half-written answer looks like. It is still shown as code: the alternative
     is prose that changes shape when the closing fence arrives. */
  text.split('```').forEach((block, i) => {
    if(i % 2) frag.appendChild(el('pre','out', block.replace(/^[a-z]*\n/i, '')));
    else if(block.trim()) blocks(block, frag, 0);
  });
  return frag;
}
/* ---- end markdown ---- */

/* Raw tool names read as the machine's word order. One table, two tenses. */
const VERB = {
  browser_navigate:['Navigating','Navigated'], browser_click:['Clicking','Clicked'],
  browser_click_at:['Clicking','Clicked'],     browser_type:['Typing','Typed'],
  browser_press_key:['Pressing','Pressed'],    browser_read_text:['Reading','Read'],
  browser_read_html:['Reading','Read'],        browser_snapshot:['Inspecting','Inspected'],
  browser_evaluate:['Evaluating','Evaluated'], browser_take_screenshot:['Capturing','Captured'],
  browser_watch:['Watching','Watched'],
  browser_select_option:['Choosing','Chose'],
  session_new_page:['Opening tab','Opened tab'],   session_select_page:['Switching tab','Switched tab'],
  session_close_page:['Closing tab','Closed tab'], session_list_pages:['Listing tabs','Listed tabs'],
  session_start:['Starting browser','Started browser'],
  browser_open:['Opening browser','Opened browser'],
  browser_close:['Closing browser','Closed browser'],
  browser_list:['Listing browsers','Listed browsers'],
  browser_focus:['Switching browser','Switched browser'],
  session_list:['Listing sessions','Listed sessions'],
  session_forget:['Deleting session','Deleted session'],
  session_status:['Checking session','Checked session']
};
const LEAD = /^(I will |I'll |I am |I'm |Let me |Now I will |Now I'll )/i;
/* ⛔ MEASURED IN CHARACTERS, SPENT IN PIXELS - the same defect this project
   recorded when `ch` was mistaken for a character, one surface later. The
   label track is 416px wide at the default split, the mono face is 7.15px a
   character at 13px and the verb in front eats about 67, so the row shows
   about FORTY-EIGHT. The branch accepted a hundred and twenty. Counted on a
   live transcript: 43 rows of 108 were cut off AND had their disclosure
   removed, so the one thing that could have shown the rest was gone. */
const LONG = 48;

const thread = $('thread'), anchor = $('anchor'), log = $('log');
let turn = null, live = null, hold = null, n = 0, t0 = 0, timer = 0;
let busyNow = false, queued = null, pinned = false, settle = 0;

