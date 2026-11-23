// 島の謎（昔の住人の手記・5枚）：その場所（物）をタップした人にだけ分かる。ヒントは出さない。
// 見つけたページは端末に覚えておく。文はぱっと読めないように変換して入れてある（ネタバレよけ。暗号ではない）。
//   1 沖の小島（東の海）  2 池（日本時間の夜 20〜4時だけ）  3 昔の住人の跡（続けて3回）  4 高原の頂上  5 クマ（ステージが「歌」の時間だけ）
const K = 'mujintou-1123';
const DATA = ["FlcdS1RUTZashNKznk9ZSksaVlVVD9KwodDs24/a2Jfu3suslNGyy5HS4Iv57pO6lNKysYvF3ors9obWstKwi9Dv94nowJft986ws9Gx5pbr5Y307pCVgdKwuIX904rv+Iz0h9KwttDt94no/Zfu286yotGw3pbr5Y307p2HgdKzuI70wYzf/oz0oNKwjNDs7Inr5pfu886wmtGz71cX", "FlcdS1RUTZasjtKzko70/Yrs/4z0lBMdEhEZV1BJTJHL6c6wmtGyx5bo4o31x5atsNeDk470xIzU4Yz0g9augdDs+YP0/Jfu+si0uNGx5pbq64js05asmtKznIXT4Yrv/Iz0h9KwttDt94no/Zft+c6wntGy4Jbryo31x5atsNizoI70/Yrs/4z0lNKwktDt90gU", "FlcdS1RUTZasutKzrI70y0tCVE0BDwsRENbO9InoxZHnzs6zotGyzZLd8431wJatsNKzt470y4rvxIz3vtiaqtDs8Ynoxpfu5s6zvNGy5pbo4IbS5JasrtKyso70+Yrv2orGm9KwnNbQ14np7JHixc6zo9GyyZbr+I318JCNhde7s473+IzR7Iz3odKwmNDs8Ynr5pfu886wmtGz71cX", "FlcdS1RUTZasn9Kwvo70/UtCVE0BDwsRENXC+4zwx5fu5s6wotGyypLrwo32/ZasrtKzt4709Yru9onAmtKwnNb95Ino/Zfu886wn9qZ3Zbr4o3145atsNKzt470zorv/4fTptKwltDs5InoyJfu+s6zvdGx5pbrwYrLzpasqdKzlY716EsT", "FlcdS1RUTZast9KzrE9ZSksaVlVVD9i8h9Ds2onp75LM286wn9Gxwpbp9431xJass9KzqY70+4rv64z1r9ecvtDs+Y/M05fu+M6wm9Gx6ZbrzY31z5asktKzrI716I/D+Iz0jtKwlNDs8Ynr4pfuxc6xsNGy4Jbryo31x52SpdKzpI70zIrv+4z3odKzudDt90gU"];
const FINAL = 'FlcdS1RUTZasutKzu4734Irvy4z0jBMdEhEZV1BJTJfu986zutSqxJbq6IjB2Jasn9Sioo70+Yrv8oz0itKxs9Ds24nr45fu4s6wvdqM+Zbryo31yZasvNKzrI716I7J9Yz0stKwk9Ds2onp75fu6M6wn9e25Jbrx4ji1pasidm6rI73+Izpzoz0tNKxsNHt4Yjp+pfu5s6wn9e25Zbrxo307pastdKzl4704Yzdwoz0g9Kym9Dv0Ynq+Jfu0s6xsxBO';
function dec(s) {
  const b = Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  for (let i = 0; i < b.length; i++) b[i] ^= K.charCodeAt(i % K.length);
  return JSON.parse(new TextDecoder().decode(b));
}
const STORE = 'mujintou.notes';
function load() {
  try { return new Set(JSON.parse(localStorage.getItem(STORE) || '[]')); } catch { return new Set(); }
}
function save(set) {
  try { localStorage.setItem(STORE, JSON.stringify([...set])); } catch { /* 保存できない環境 */ }
}
export const SECRET_COUNT = DATA.length;
// n：0〜4。{ n, page, total, found, isNew, final }
export function reveal(n) {
  const found = load();
  const isNew = !found.has(n);
  found.add(n);
  save(found);
  return { n, page: dec(DATA[n]), total: DATA.length, found: found.size, isNew, final: found.size >= DATA.length ? dec(FINAL) : null };
}
