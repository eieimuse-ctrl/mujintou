// ep3 録画：node ep3/rec.mjs <story.json> [--test]
//   → build/ep3/<story名>/frames/f00000.jpg … ＋ track.jsonl（各コマの島民の頭・足の画面位置）
// サイトはこのリポジトリをそのまま配信する（stage のコピーは作らない）。データは台本の cast だけを差し替えて渡す。
// 再開可能：できているコマは飛ばす。--test は 0・中央・最後の3コマだけ 540×960 で撮る。
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../..');
const args = process.argv.slice(2);
const TEST = args.includes('--test');
const storyPath = path.resolve(args.find((x) => !x.startsWith('--')) || '');
const story = JSON.parse(fs.readFileSync(storyPath, 'utf8'));
const NAME = path.basename(storyPath, '.json');
const OUT = path.join(HERE, '../build/ep3', NAME + (TEST ? '-test' : ''));
const FPS = story.fps || 24;
const BASE_T = Date.parse(story.baseTime || '2026-11-19T09:00:00+09:00');
const W = 540, H = 960, DSF = TEST ? 1 : 2; // 完成は 1080×1920

// Chrome：環境変数 CHROME があればそれ、無ければ制作マシンの chrome-headless-shell、最後に google-chrome
function findChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const base = path.join(process.env.HOME, '.cache/puppeteer/chrome-headless-shell');
  if (fs.existsSync(base)) {
    for (const v of fs.readdirSync(base).sort().reverse()) {
      const p = path.join(base, v, 'chrome-headless-shell-linux64/chrome-headless-shell');
      if (fs.existsSync(p)) return p;
    }
  }
  return '/usr/bin/google-chrome';
}

// 台本に出る人だけの名簿・島の状態
const roster = JSON.parse(fs.readFileSync(path.resolve(path.dirname(storyPath), story.roster), 'utf8'));
const byId = new Map(roster.islanders.map((p) => [p.id, p]));
const castIds = [...new Set([...(story.cast || []), ...(story.groups || []).flatMap((g) => g.members || [])])];
const castPeople = castIds.map((id) => byId.get(id)).filter(Boolean).map((p) => ({ ...p, joinedDay: 1, ...(story.override?.[p.id] || {}), ...(story.overrideAll || {}) }));
const missing = castIds.filter((id) => !byId.has(id));
if (missing.length) console.log('名簿に無いので出さない:', missing.join(', '));
const state = JSON.parse(fs.readFileSync(path.join(REPO, 'data/state.json'), 'utf8'));
Object.assign(state, { day: story.day || 3, sample: false, base: story.base ?? { name: '中央の広場', x: 0, z: 5, decidedDay: 2 }, currentVote: null, buildings: story.buildings || [], forestRoad: story.forestRoad || null });
const DATA = {
  state,
  islanders: { updatedAt: '2026-11-19', islanders: castPeople },
  drifters: { updatedAt: '2026-11-19', drifters: [] },
};

// 静的サーバ（リポジトリ直下）
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const f = path.join(REPO, u === '/' ? '/index.html' : u);
  if (!f.startsWith(REPO) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

const browser = await puppeteer.launch({
  executablePath: findChrome(),
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--js-flags=--max-old-space-size=512'],
  protocolTimeout: 300000,
});
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: DSF });
page.on('pageerror', (e) => console.log('pageerror:', String(e).slice(0, 300)));
await page.setRequestInterception(true);
page.on('request', (req) => {
  const u = req.url();
  if (!u.startsWith(`http://127.0.0.1:${PORT}/`)) return req.abort(); // 外へは出ない（Firebase も読まない＝同じ結果になる）
  const m = u.match(/\/data\/(state|islanders|drifters)\.json/);
  if (m) return req.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(DATA[m[1]]) });
  return req.continue();
});
await page.goto(`http://127.0.0.1:${PORT}/index.html?debug&nosw&freeze&t=${BASE_T}`, { waitUntil: 'load', timeout: 120000 });
await page.waitForFunction(() => window.__island, { timeout: 120000 });
await page.evaluate((bt) => { window.requestAnimationFrame = () => 0; window.__BASE_T = bt; }, BASE_T);
await page.evaluate(fs.readFileSync(path.join(HERE, 'lib/stage.js'), 'utf8'));
// 建物の形（buildings.js）を、組み上がる小道具のために読み込んでおく
await page.evaluate(async () => {
  const m = await import('/js/buildings.js');
  window.__BUILD_DEFS = {};
  for (const [k, f] of Object.entries(m.BUILDING_TYPES)) window.__BUILD_DEFS[k] = f();
});
const env = await page.evaluate((s) => window.__ep3.setup(s), story);
console.log(NAME, 'cast', env.n, 'chrome', await browser.version());

const FR = path.join(OUT, 'frames');
fs.mkdirSync(FR, { recursive: true });
fs.writeFileSync(path.join(OUT, 'env.json'), JSON.stringify({ ...env, fps: FPS, duration: story.duration, chrome: await browser.version() }));
const N = Math.round(story.duration * FPS);
const only = process.env.FRAMES ? process.env.FRAMES.split(',').map(Number) : null;
const list = only || (TEST ? [0, Math.floor(N / 2), N - 1] : [...Array(N).keys()]);
const trackFile = path.join(OUT, 'track.jsonl');
const t0 = Date.now();
let done = 0;
for (const i of list) {
  const file = path.join(FR, `f${String(i).padStart(5, '0')}.jpg`);
  if (fs.existsSync(file) && fs.statSync(file).size > 1000) continue;
  const t = i / FPS;
  const r = await page.evaluate((t, w, h) => window.__ep3.frame(t, w, h, 0.93), t, W, H);
  fs.writeFileSync(file + '.tmp', Buffer.from(r.b64, 'base64'));
  fs.renameSync(file + '.tmp', file);
  fs.appendFileSync(trackFile, JSON.stringify({ i, t: +t.toFixed(4), people: r.people }) + '\n');
  done++;
  if (done % 24 === 0) console.log(NAME, i, '/', N, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  if (process.env.MAX_SEC && (Date.now() - t0) / 1000 > Number(process.env.MAX_SEC)) { console.log('MAX_SEC に達したので中断（再実行で続きから）'); break; }
}
console.log(NAME, 'done', done, 'new frames', ((Date.now() - t0) / 1000).toFixed(0) + 's');
await browser.close();
server.close();
