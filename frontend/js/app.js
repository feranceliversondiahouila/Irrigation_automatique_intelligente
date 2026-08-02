// ===================================================================
// IrrigAI — frontend JS : thème clair/sombre, appels à l'API FastAPI,
// mise à jour du DOM. Aucune dépendance externe.
// ===================================================================

const API = ""; // même origine : le backend sert aussi ce frontend

// -------------------------------------------------------------
// Thème clair / sombre (persisté dans le navigateur)
// -------------------------------------------------------------
const themeToggle = document.getElementById("theme-toggle");

function appliquerTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
  localStorage.setItem("irrigai-theme", theme);
}

const themeInitial =
  localStorage.getItem("irrigai-theme") ||
  (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
appliquerTheme(themeInitial);

themeToggle.addEventListener("click", () => {
  const actuel = document.documentElement.getAttribute("data-theme");
  appliquerTheme(actuel === "dark" ? "light" : "dark");
});

// -------------------------------------------------------------
// Sliders : afficher la valeur en direct à côté du label
// -------------------------------------------------------------
function brancherAffichageSlider(input) {
  const out = document.querySelector(`[data-out="${input.id}"]`);
  if (!out) return;
  const maj = () => (out.textContent = input.value);
  input.addEventListener("input", maj);
  maj();
}
document.querySelectorAll("input[type='range']").forEach(brancherAffichageSlider);

// -------------------------------------------------------------
// Section "Paramètres" — prédiction ponctuelle
// -------------------------------------------------------------
async function predireArrosage() {
  const body = {
    humidite_sol: Number(document.getElementById("hum_sol").value),
    temperature_air: Number(document.getElementById("temp_air").value),
    humidite_air: Number(document.getElementById("hum_air").value),
    pluie_prevue_mm: Number(document.getElementById("pluie").value),
    type_sol: document.getElementById("sol").value,
    type_culture: document.getElementById("culture").value,
  };
  const sortie = document.getElementById("resultat-prediction");
  sortie.textContent = "Analyse en cours…";
  try {
    const res = await fetch(`${API}/api/predire`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    sortie.textContent = data.message ?? "Erreur inattendue.";
  } catch (e) {
    sortie.textContent = "❌ Impossible de contacter le serveur. Le backend est-il lancé ?";
  }
}
document.getElementById("btn-predire").addEventListener("click", predireArrosage);

document.getElementById("btn-effacer").addEventListener("click", () => {
  document.getElementById("hum_sol").value = 30;
  document.getElementById("temp_air").value = 28;
  document.getElementById("hum_air").value = 50;
  document.getElementById("pluie").value = 0;
  ["hum_sol", "temp_air", "hum_air", "pluie"].forEach((id) =>
    document.getElementById(id).dispatchEvent(new Event("input"))
  );
  document.getElementById("resultat-prediction").textContent = "—";
});

// -------------------------------------------------------------
// Dashboard : configuration (sols/cultures/zones), météo, réservoir
// -------------------------------------------------------------
let ZONES = [];
let derniereMeteo = null;

function remplirSelect(id, options) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = options.map((o) => `<option value="${o}">${o}</option>`).join("");
}

async function chargerConfig() {
  const res = await fetch(`${API}/api/config`);
  const data = await res.json();
  ZONES = data.zones;

  remplirSelect("sol", data.sols);
  remplirSelect("culture", data.cultures);
  remplirSelect("s-sol", data.sols);
  remplirSelect("s-culture", data.cultures);

  const grid = document.getElementById("zones-grid");
  grid.innerHTML = "";
  ZONES.forEach((zone, i) => {
    const div = document.createElement("div");
    div.className = "zone-card";
    div.innerHTML = `
      <h4>${zone.nom}</h4>
      <p>${zone.sol} / ${zone.culture}</p>
      <label>Humidité du sol (%) — <span data-out="zone-${i}">${zone.humidite_defaut}</span>
        <input type="range" id="zone-${i}" min="0" max="100" value="${zone.humidite_defaut}">
      </label>
      <p class="zone-status" id="zone-status-${i}">—</p>
    `;
    grid.appendChild(div);
  });
  document.querySelectorAll("#zones-grid input[type='range']").forEach(brancherAffichageSlider);
}

async function recupererMeteo() {
  const ville = document.getElementById("ville").value.trim();
  const resumeEl = document.getElementById("meteo-resume");
  resumeEl.textContent = "Recherche en cours…";
  try {
    const res = await fetch(`${API}/api/meteo?ville=${encodeURIComponent(ville)}`);
    if (!res.ok) throw new Error("introuvable");
    const data = await res.json();
    derniereMeteo = data;
    const pluieTxt = data.pluie_3_jours
      .map(([d, mm]) => `${d.slice(5)} : ${mm.toFixed(1)}mm`)
      .join(" / ");
    resumeEl.textContent =
      `📍 ${data.ville} — ${data.temperature_actuelle.toFixed(1)}°C, ` +
      `${data.humidite_air_actuelle.toFixed(0)}% d'humidité de l'air\n` +
      `🌧️ Pluie prévue (3 jours) : ${pluieTxt} — total ${data.pluie_totale_72h_mm.toFixed(1)} mm`;
  } catch (e) {
    derniereMeteo = null;
    resumeEl.textContent =
      "❌ Ville introuvable ou API météo injoignable. Les zones utiliseront des valeurs par défaut.";
  }
}
document.getElementById("btn-meteo").addEventListener("click", recupererMeteo);

function majJauge(reservoir) {
  const bar = document.getElementById("gauge-bar");
  const pct = reservoir.niveau_pct;
  bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  bar.style.background =
    pct > 40 ? "var(--success)" : pct > 20 ? "var(--warning)" : "var(--danger)";
  document.getElementById("reservoir-detail").textContent =
    `${reservoir.niveau_l.toFixed(0)} / ${reservoir.capacite_l.toFixed(0)} L` +
    (reservoir.en_alerte ? "  ⚠️ Niveau bas, pensez à recharger." : "");
}

async function chargerReservoir() {
  const res = await fetch(`${API}/api/reservoir`);
  majJauge(await res.json());
}

async function analyserZones() {
  const humidites = ZONES.map((_, i) => Number(document.getElementById(`zone-${i}`).value));
  const body = {
    humidites_sol: humidites,
    temperature_air: derniereMeteo?.temperature_actuelle ?? 25,
    humidite_air: derniereMeteo?.humidite_air_actuelle ?? 50,
    pluie_prevue_mm: derniereMeteo?.pluie_aujourdhui_mm ?? 0,
  };

  const zonesResultat = document.getElementById("zones-resultat");
  zonesResultat.textContent = "Analyse en cours…";
  try {
    const res = await fetch(`${API}/api/zones/analyser`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    const labels = {
      arrosage: "🔴 Arrosage requis",
      surveiller: "🟠 À surveiller",
      stable: "🟢 Sol stable",
    };
    data.zones.forEach((z, i) => {
      const el = document.getElementById(`zone-status-${i}`);
      el.textContent = `${labels[z.statut]} (confiance ${(z.confiance * 100).toFixed(0)}%)`;
      el.className = `zone-status status-${z.statut}`;
    });

    zonesResultat.textContent =
      `${data.message_pluie}\n💧 Eau utilisée aujourd'hui : ${data.total_litres_jour.toFixed(0)} L`;

    majJauge(data.reservoir);
  } catch (e) {
    zonesResultat.textContent = "❌ Impossible de contacter le serveur.";
  }
}
document.getElementById("btn-analyser").addEventListener("click", analyserZones);

document.getElementById("btn-recharger").addEventListener("click", async () => {
  const litres = Number(document.getElementById("recharge-input").value);
  await fetch(`${API}/api/reservoir/recharger`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ litres }),
  });
  chargerReservoir();
});

async function chargerEconomieEau() {
  const res = await fetch(`${API}/api/economie-eau`);
  const data = await res.json();
  document.getElementById("economie-eau").textContent = data.texte;
}

// -------------------------------------------------------------
// Analyse : simulateur « et si… »
// -------------------------------------------------------------
document.getElementById("btn-comparer").addEventListener("click", async () => {
  const body = {
    humidite_sol: Number(document.getElementById("s-hum-sol").value),
    humidite_air: Number(document.getElementById("s-hum-air").value),
    pluie_prevue_mm: Number(document.getElementById("s-pluie").value),
    type_sol: document.getElementById("s-sol").value,
    type_culture: document.getElementById("s-culture").value,
    temp_base: Number(document.getElementById("s-temp-base").value),
    temp_hypothese: Number(document.getElementById("s-temp-hyp").value),
  };
  const sortie = document.getElementById("comparaison-resultat");
  sortie.textContent = "Comparaison en cours…";
  try {
    const res = await fetch(`${API}/api/comparer-scenarios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    sortie.textContent =
      `🌡️ Scénario actuel (${body.temp_base}°C) : ${data.scenario_actuel}\n\n` +
      `🌡️ Scénario hypothétique (${body.temp_hypothese}°C) : ${data.scenario_hypothese}`;
  } catch (e) {
    sortie.textContent = "❌ Impossible de contacter le serveur.";
  }
});

// -------------------------------------------------------------
// Initialisation
// -------------------------------------------------------------
(async function init() {
  await chargerConfig();
  await chargerReservoir();
  await chargerEconomieEau();
})();
