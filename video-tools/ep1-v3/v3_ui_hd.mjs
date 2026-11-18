// v3: transparent UI layers of the real PWA (390x844 @3x = 1170x2532) for the "check it in the app" part.
// Fixes v3_ui.mjs, which typed into #search without opening the 島民 tab (its u2_type*.png show the island tab).
// The roster request is answered with ONE islander named 「あなた」 (video mock-up only; site/ is not touched).
// The 3-D canvas and the 3-D labels are hidden, so no islander figure is ever drawn — the compositor puts
// take p (empty island) underneath.
//   node v3_ui_hd.mjs        -> build/ui3/hd/h*.png + rects.json   (needs the HTTP server on 8773)
import fs from 'node:fs';
import puppeteer from 'puppeteer-core';
const EXE = process.env.HOME + '/.cache/puppeteer/chrome-headless-shell/linux-157.0.8103.50/chrome-headless-shell-linux64/chrome-headless-shell';
const OUT = process.env.HOME + '/workspace/mujintou/video/build/ui3/hd';
fs.mkdirSync(OUT, { recursive: true });
const T = Date.parse('2026-11-17T10:00:00+09:00');
const YOU = { updatedAt: '2026-11-17', islanders: [{ id: 'you', name: 'あなた', joinedDay: 1, since: '2026-11-17', home: 'beach', relationships: [] }] };
const browser = await puppeteer.launch({ executablePath: EXE, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'], protocolTimeout: 90000 });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
page.on('pageerror', (e) => console.log('pageerror:', String(e).slice(0, 200)));
await page.setRequestInterception(true);
page.on('request', (r) => (/data\/islanders\.json/.test(r.url()) ? r.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(YOU) }) : r.continue()));
await page.goto(`http://127.0.0.1:8773/index.html?debug&nosw&freeze&t=${T}`, { waitUntil: 'networkidle0', timeout: 90000 });
await page.waitForFunction(() => window.__island, { timeout: 60000 });
await new Promise((r) => setTimeout(r, 2500));
// stop the app's render loop: at 3x the hidden SwiftShader canvas kept the GPU busy and
// Page.captureScreenshot timed out once the sheet opened (the camera starts moving)
await page.evaluate(() => { window.requestAnimationFrame = () => 0; });
await page.addStyleTag({ content: 'html,body,#app,#stage{background:transparent!important} #scene,#labels,#loading,#toast{visibility:hidden!important} #scene{display:none!important} *{caret-color:transparent!important}' });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const snap = async (name) => { await page.screenshot({ path: `${OUT}/${name}.png`, omitBackground: true }); console.log('saved', name); };
const rect = (sel) => page.evaluate((s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height].map((v) => +v.toFixed(1)); }, sel);
const rects = {};
const keep = async (names) => { for (const s of names) rects[s] = await rect(s); };

await snap('h0_home');
await keep(['#hud', '#vote-chip', '#recenter', '#tabs', '#tabs [data-tab="islanders"]', '#tabs [data-tab="island"]']);

await page.click('#tabs [data-tab="islanders"]');
await wait(1200);
await snap('h1_list');
await keep(['#sheet', '#search', '#search-form', '#list-meta', '#islander-list', '#islander-list li']);
console.log('sheet state', await page.evaluate(() => document.body.dataset.sheet));

for (const [i, part] of ['あ', 'あな', 'あなた'].entries()) {
  await page.evaluate((v) => { const s = document.querySelector('#search'); s.value = v; s.dispatchEvent(new Event('input', { bubbles: true })); }, part);
  await wait(400);
  await snap(`h2_type${i + 1}`);
}
await keep(['#list-meta', '#islander-list li']);
rects.listRowsHTML = await page.evaluate(() => document.querySelector('#islander-list').innerText.slice(0, 300));

await page.evaluate(() => (document.querySelector('#islander-list li button') || document.querySelector('#islander-list li a') || document.querySelector('#islander-list li')).click());
await wait(1500);
// the 「いま」 line is filled by the app's render loop (ui.setNow(sim.status(selected, t)) every 500 ms),
// which is stopped here -> build the same DOM by hand from the same sim call (islander 0 = あなた)
rects.now = await page.evaluate(() => {
  const a = window.__island; const st = a.sim.status(0, a.clock.now());
  const mk = (tag, cls, text) => Object.assign(document.createElement(tag), { className: cls, textContent: text });
  const nl = document.querySelector('.now-line');
  nl.replaceChildren(...[mk('span', 'now-tag', st.label ? `いま・${st.label}` : 'いま'), mk('p', 'now-text', st.text), st.next ? mk('p', 'now-next', `このあと：${st.next}`) : null].filter(Boolean));
  return st;
});
await wait(300);
await snap('h3_detail');
await keep(['#sheet', '#view-detail', '.now-line', '.now-tag', '.now-text', '.now-next', '#view-detail h2', '#view-detail img, #view-detail canvas']);
rects.detailText = await page.evaluate(() => document.querySelector('#view-detail').innerText.slice(0, 400));
rects.sheetState = await page.evaluate(() => document.body.dataset.sheet);
fs.writeFileSync(`${OUT}/rects.json`, JSON.stringify(rects, null, 1));
console.log(JSON.stringify(rects));
await browser.close();
