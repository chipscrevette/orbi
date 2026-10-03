// Le film, version rythmée : 18 s calées sur une pulsation à 128 bpm (un temps = 0,469 s).
// Chaque image est une fonction pure du temps : rendre(t).
const $ = (id) => document.getElementById(id);
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const p = (t, a, b) => clamp((t - a) / (b - a));
const sortie = (x) => 1 - Math.pow(1 - x, 3);
const vive = (x) => 1 - Math.pow(1 - x, 5);
const ressort = (x) => { const c = 1.9; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const coup = (t, a, d = 0.22) => Math.sin(p(t, a, a + d) * Math.PI) * (t >= a ? 1 : 0); // une impulsion 0 → 1 → 0
const TEMPS = 60 / 128;
const QUESTION = 'Je veux construire un abri de jardin de 10 m² au 15 avenue de la Marne à Biarritz. Est-ce possible ?';
const CITATION = "Tout point des constructions est éloigné du point le plus proche de la limite séparative arrière d’une distance horizontale (D) au moins égale à la différence d’altitude entre ces deux points moins 3,00 m : H ≤ D + 3, soit D ≥ H – 3.";

function montre(el, o, dy = 0, s = 1, dx = 0) { el.style.opacity = o; el.style.transform = `translate(${dx}px, ${dy}px) scale(${s})`; }
// une scène entre en glissant depuis la droite et sort en glissant vers la gauche, en ~0,25 s
function scene(el, t, a, b) {
  const entree = vive(p(t, a, a + 0.28)), fin = vive(p(t, b - 0.25, b));
  el.style.opacity = t < a || t > b ? 0 : Math.min(1, entree * 1.4) * (1 - fin);
  el.style.transform = `translateX(${(1 - entree) * 220 - fin * 260}px) scale(${1 + 0.035 * p(t, a, b)})`; // poussée de caméra lente
}
function brique(el, t, t0) {
  const chute = sortie(p(t, t0, t0 + 0.32));
  const choc = p(t, t0 + 0.32, t0 + 0.75);
  const ecrase = Math.sin(choc * Math.PI) * (1 - choc) * 0.55;
  el.style.opacity = t < t0 ? 0 : 1;
  el.style.transform = `translateY(${(1 - chute) * -760}px) scale(${1 + ecrase * 0.38}, ${1 - ecrase * 0.42})`;
}
function etincelles(el, t, t0, x, y) {
  el.style.left = x + 'px'; el.style.top = y + 'px';
  const a = p(t, t0, t0 + 0.15);
  el.style.opacity = a * (t > 0 ? 1 : 0); el.style.transform = `scale(${0.5 + 0.5 * ressort(a)})`;
}

let carte;
async function preparer() {
  carte = await (await fetch('carte.json')).json();
  $('carteSvg').innerHTML = carte.chemins.map((c) => `<path d="${c.d}" fill="${c.couleur}" fill-opacity="${c.code === 'UAs' ? 0.62 : 0.28}" stroke="${c.couleur}" stroke-width="${c.code === 'UAs' ? 3 : 1.2}" stroke-opacity=".9"/>`).join('')
    + `<circle id="halo" cx="${carte.point[0]}" cy="${carte.point[1]}" r="14" fill="#3d9bff" opacity=".3"/><circle cx="${carte.point[0]}" cy="${carte.point[1]}" r="11" fill="#1f68e8" stroke="#fff" stroke-width="4"/>`;
  await document.fonts.ready;
  await Promise.all([...document.images].map((i) => i.decode()));
}

function rendre(t) {
  // ----- 1. l'accroche (0 → 2,6 s) : trois mots sur trois temps, la brique tombe sur le quatrième
  scene($('s1'), t, -1, 2.6);
  [...document.querySelectorAll('.mot')].forEach((m, i) => {
    const a = 0.12 + i * TEMPS * 0.75;
    const k = p(t, a, a + 0.2);
    m.style.opacity = k > 0 ? 1 : 0;
    m.style.transform = `translateY(${(1 - vive(k)) * 50}px) scale(${0.7 + 0.3 * ressort(k)})`;
  });
  $('curseur')?.remove();
  brique($('orbi1'), t, 0.95);
  etincelles($('et1'), t, 1.45, 1790, 350);
  montre($('sous'), p(t, 1.5, 1.7), 14 * (1 - sortie(p(t, 1.5, 1.7))));

  // ----- 2. la question (2,55 → 6,1 s), puis 3. la réponse, dans la même fenêtre (→ 11,1 s)
  scene($('s2'), t, 2.55, 11.1);
  const nq = Math.round(QUESTION.length * p(t, 2.9, 3.75));
  const tape = t < 3.95 ? QUESTION.slice(0, nq) : '';
  $('saisieTexte').textContent = tape || 'Posez votre question…';
  $('saisieTexte').className = 'abs' + (tape ? '' : ' vide');
  $('envoyer').style.transform = `scale(${1 - 0.16 * coup(t, 3.82, 0.18)})`;
  montre($('question'), p(t, 3.92, 4.08), 24 * (1 - vive(p(t, 3.92, 4.1))));
  const enTravail = Math.min(p(t, 4.0, 4.15), 1 - p(t, 6.05, 6.15));
  montre($('travail'), enTravail, 30 * (1 - vive(p(t, 4.0, 4.2))));
  const lignes = [...document.querySelectorAll('.ligne')];
  const coches = [4.3, 4.53, 4.77, 5.7, 5.85, 6.0]; // sur les croches, la longue étape fait la course
  let debut = 4.12;
  lignes.forEach((l, i) => {
    const a = coches[i];
    const faite = t >= a, active = !faite && t >= debut;
    l.className = 'ligne' + (faite ? ' faite' : active ? ' active' : '');
    const temps = l.querySelector('.temps');
    temps.textContent = faite ? l.dataset.s : active && i === 3 ? (70.9 * p(t, debut, a)).toFixed(1).replace('.', ',') + ' s' : '';
    const rond = l.querySelector('.rond');
    rond.style.transform = active ? `rotate(${t * 720}deg)` : faite ? `scale(${1 + 0.35 * coup(t, a, 0.16)})` : '';
    debut = a;
  });
  const total = 78.9 * p(t, 4.12, 6.0);
  $('total').textContent = total >= 60 ? `1 min ${String(Math.round(total - 60)).padStart(2, '0')} s` : total.toFixed(1).replace('.', ',') + ' s';
  montre($('reel'), Math.min(p(t, 4.4, 4.55), 1 - p(t, 6.05, 6.15)), 0);
  montre($('resume'), p(t, 6.18, 6.3), 0);
  // le verdict claque sur le temps fort
  const r = p(t, 6.25, 6.5);
  montre($('reponse'), r, 50 * (1 - vive(r)), 0.94 + 0.06 * ressort(r));
  $('verdict').style.transform = `scale(${1 + 0.07 * coup(t, 6.5, 0.24)})`;
  const c = p(t, 6.5, 6.8);
  montre($('carte'), c, 0, 0.9 + 0.1 * ressort(c), 60 * (1 - vive(c)));
  $('carteSvg').style.transform = `scale(${1.5 - 0.5 * sortie(p(t, 6.5, 8.2))})`;
  const halo = $('halo');
  if (halo) { const h = (t / TEMPS) % 1; halo.setAttribute('r', 12 + 26 * h); halo.setAttribute('opacity', 0.45 * (1 - h)); }
  montre($('etiquette'), p(t, 6.95, 7.1), 0);
  montre($('lieu'), p(t, 6.75, 6.9), 12 * (1 - vive(p(t, 6.75, 6.9))));
  montre($('regle'), p(t, 6.98, 7.12), 12 * (1 - vive(p(t, 6.98, 7.12))));
  $('citation').textContent = CITATION.slice(0, Math.round(CITATION.length * p(t, 7.1, 8.1)));
  $('verifiee').style.opacity = p(t, 8.2, 8.3);
  $('verifiee').style.transform = `scale(${1 + 0.4 * coup(t, 8.2, 0.25)}) rotate(${-4 * coup(t, 8.2, 0.25)}deg)`;
  montre($('demarche'), p(t, 8.65, 8.8), 10 * (1 - vive(p(t, 8.65, 8.8))));
  $('saisie').style.opacity = 1 - p(t, 6.1, 6.25);

  // ----- 4. la preuve (11 → 15 s) : trois cartes sur trois temps
  scene($('s4'), t, 11.0, 15.0);
  montre($('preuveTitre'), p(t, 11.15, 11.35), 24 * (1 - vive(p(t, 11.15, 11.35))));
  [['st1', 11.6], ['st2', 11.6 + TEMPS], ['st3', 11.6 + 2 * TEMPS]].forEach(([id, a]) => {
    const k = p(t, a, a + 0.3);
    montre($(id), k, 70 * (1 - vive(k)), 0.85 + 0.15 * ressort(k));
  });
  $('nbTests').textContent = Math.round(1108 * sortie(p(t, 11.6 + TEMPS, 12.6))).toLocaleString('fr-FR');

  // ----- 5. la fin (14,9 → 18 s)
  scene($('s5'), t, 14.9, 99);
  brique($('orbi5'), t, 15.0);
  etincelles($('et5'), t, 15.5, 1190, 120);
  montre($('nom'), p(t, 15.45, 15.65), 26 * (1 - vive(p(t, 15.45, 15.65))), 0.9 + 0.1 * ressort(p(t, 15.45, 15.65)));
  montre($('devise'), p(t, 15.85, 16.05), 16 * (1 - vive(p(t, 15.85, 16.05))));
  montre($('lien'), p(t, 16.3, 16.45), 0);
}
window.rendre = rendre;
window.pret = preparer().then(() => { rendre(0); return true; });
