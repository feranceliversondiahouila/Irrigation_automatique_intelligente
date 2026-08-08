const API = "";
let TOKEN = localStorage.getItem("irrigai-token") || null;
let MOI = null;
let ZONES = [];

// ---------- Thème ----------
const themeToggle = document.getElementById("theme-toggle");
function appliquerTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  themeToggle.textContent = t === "dark" ? "☀️" : "🌙";
  localStorage.setItem("irrigai-theme", t);
}
appliquerTheme(localStorage.getItem("irrigai-theme") ||
  (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
themeToggle.addEventListener("click", () => {
  appliquerTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
});

// ---------- Fetch authentifié ----------
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (TOKEN) headers["Authorization"] = `Bearer ${TOKEN}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401) { deconnexion(); throw new Error("Session expirée"); }
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || res.statusText); }
  return res.headers.get("content-type")?.includes("json") ? res.json() : res;
}

// ---------- Connexion / déconnexion ----------
document.getElementById("btn-login").addEventListener("click", async () => {
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  const err = document.getElementById("login-erreur");
  err.textContent = "";
  try {
    const res = await fetch(`${API}/api/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error("Identifiants incorrects.");
    const data = await res.json();
    TOKEN = data.token; MOI = data;
    localStorage.setItem("irrigai-token", TOKEN);
    afficherApp();
  } catch (e) { err.textContent = "❌ " + e.message; }
});

function deconnexion() {
  TOKEN = null; MOI = null;
  localStorage.removeItem("irrigai-token");
  document.getElementById("app").hidden = true;
  document.getElementById("login-screen").hidden = false;
}
document.getElementById("btn-logout").addEventListener("click", async () => {
  try { await api("/api/logout", { method: "POST" }); } catch (e) {}
  deconnexion();
});

async function afficherApp() {
  document.getElementById("login-screen").hidden = true;
  document.getElementById("app").hidden = false;
  document.getElementById("user-badge").textContent =
    `${MOI.username}${MOI.is_superuser ? " (admin)" : ""}`;
  document.getElementById("nav-admin").hidden = !MOI.is_superuser;
  document.getElementById("admin").hidden = !MOI.is_superuser;

  await chargerConfig();
  await chargerZones();
  await chargerReservoirs();
  await chargerEconomieEau();
  await chargerJournal();
  if (MOI.is_superuser) await chargerUsers();
}

// ---------- Init : session déjà enregistrée ? ----------
(async function init() {
  if (!TOKEN) return;
  try {
    MOI = await api("/api/whoami");
    afficherApp();
  } catch (e) { deconnexion(); }
})();

// ---------- Sliders génériques ----------
function brancherSlider(input) {
  const out = document.querySelector(`[data-out="${input.id}"]`);
  if (!out) return;
  const maj = () => (out.textContent = input.value);
  input.addEventListener("input", maj);
  maj();
}
document.querySelectorAll("input[type='range']").forEach(brancherSlider);

// ---------- Config (listes déroulantes) ----------
let SOLS = [], CULTURES_SPECIFIQUES = [], CATEGORIES_CULTURE = [];
async function chargerConfig() {
  const cfg = await api("/api/config");
  SOLS = cfg.sols; CULTURES_SPECIFIQUES = cfg.cultures_specifiques; CATEGORIES_CULTURE = cfg.categories_culture;
  remplir("new-zone-sol", SOLS);
  remplir("new-zone-culture", CULTURES_SPECIFIQUES);
  remplir("s-sol", SOLS);
  remplir("s-culture", CATEGORIES_CULTURE);
}
function remplir(id, options) {
  document.getElementById(id).innerHTML = options.map((o) => `<option value="${o}">${o}</option>`).join("");
}

// ---------- Zones ----------
async function chargerZones() {
  ZONES = await api("/api/zones");
  const conteneur = document.getElementById("zones-liste");
  conteneur.innerHTML = ZONES.map((z) => `
    <div class="zone-carte" id="zone-${z.id}">
      <div class="zone-entete">
        <div>
          <h4>${z.nom}</h4>
          <p class="zone-meta">📍 ${z.ville}${z.region ? " (" + z.region + ")" : ""} — ${z.type_sol} / ${z.culture_specifique} — ${z.surface_hectares} ha</p>
        </div>
        <div class="zone-actions">
          <button class="btn-ghost btn-small" onclick="voirDiagnostic(${z.id})">🔍 Diagnostic</button>
          <button class="btn-primary btn-small" onclick="lancerCycleAuto(${z.id})">⚡ Cycle auto</button>
          ${MOI.is_superuser ? `<button class="btn-danger btn-small" onclick="supprimerZone(${z.id})">🗑️</button>` : ""}
        </div>
      </div>

      ${MOI.is_superuser ? `
      <div class="zone-humidite-edit">
        <label>💧 Humidité du sol (%)</label>
        <input type="number" id="hum-${z.id}" value="${z.humidite_sol}" min="0" max="100">
        <button class="btn-ghost btn-small" onclick="majHumidite(${z.id})">Mettre à jour</button>
      </div>
      <div class="zone-toggles">
        <label class="toggle-line"><input type="checkbox" id="auto-eau-${z.id}" ${z.arrosage_auto ? "checked" : ""} onchange="toggleAuto(${z.id}, 'arrosage_auto', this.checked)"> Arrosage automatique</label>
        <label class="toggle-line"><input type="checkbox" id="auto-pest-${z.id}" ${z.traitement_auto ? "checked" : ""} onchange="toggleAuto(${z.id}, 'traitement_auto', this.checked)"> Traitement automatique</label>
      </div>
      ` : `<p class="zone-meta">💧 Humidité du sol : ${z.humidite_sol}%</p>`}

      <div class="zone-diagnostic" id="diagnostic-${z.id}"></div>
    </div>
  `).join("") || "<p class='hint'>Aucune zone pour le moment.</p>";
}

function afficherDiagnostic(zoneId, data) {
  const el = document.getElementById(`diagnostic-${zoneId}`);
  if (data.erreur) { el.innerHTML = `<p class="info-box">❌ ${data.erreur}</p>`; return; }

  const badge = { ARROSER: "badge-arroser", SURVEILLER: "badge-surveiller", CONSERVER: "badge-conserver" }[data.decision_arrosage.action];
  let html = `
    <p class="info-box">🌦️ <strong>${data.meteo_temps_reel.ville}</strong> — ${data.meteo_temps_reel.temperature.toFixed(1)}°C,
    ${data.meteo_temps_reel.humidite_air.toFixed(0)}% air, pluie ${data.meteo_temps_reel.pluie_aujourdhui_mm.toFixed(1)}mm</p>
    <p><span class="badge ${badge}">${data.decision_arrosage.action}</span>
    (confiance ${(data.decision_arrosage.confiance * 100).toFixed(0)}%) — ${data.decision_arrosage.raison}</p>
    <p class="info-box">🌿 Santé de la culture (${data.sante_culture.score_sante}%) :<br>${data.sante_culture.diagnostics.join("<br>")}</p>
  `;
  if (data.conseils_phytosanitaires.length) {
    html += `<p class="info-box">${data.conseils_phytosanitaires.join("<br>")}</p>`;
  }
  if (data.action_automatique_eau) html += `<p class="info-box">✅ ${data.action_automatique_eau}</p>`;
  if (data.action_automatique_pesticide) html += `<p class="info-box">✅ ${data.action_automatique_pesticide}</p>`;
  if (data.recharge_pluie) html += `<p class="info-box">${data.recharge_pluie}</p>`;
  el.innerHTML = html;

  if (data.reservoirs) majJauges(data.reservoirs);
}

window.voirDiagnostic = async (zoneId) => {
  document.getElementById(`diagnostic-${zoneId}`).innerHTML = "<p class='info-box'>Analyse en cours…</p>";
  try { afficherDiagnostic(zoneId, await api(`/api/zones/${zoneId}/diagnostic`)); }
  catch (e) { document.getElementById(`diagnostic-${zoneId}`).innerHTML = `<p class="info-box">❌ ${e.message}</p>`; }
};
window.lancerCycleAuto = async (zoneId) => {
  document.getElementById(`diagnostic-${zoneId}`).innerHTML = "<p class='info-box'>Cycle en cours…</p>";
  try { afficherDiagnostic(zoneId, await api(`/api/zones/${zoneId}/cycle-auto`, { method: "POST" })); await chargerJournal(); }
  catch (e) { document.getElementById(`diagnostic-${zoneId}`).innerHTML = `<p class="info-box">❌ ${e.message}</p>`; }
};
window.majHumidite = async (zoneId) => {
  const val = Number(document.getElementById(`hum-${zoneId}`).value);
  await api(`/api/zones/${zoneId}`, { method: "PUT", body: JSON.stringify({ humidite_sol: val }) });
};
window.toggleAuto = async (zoneId, champ, valeur) => {
  await api(`/api/zones/${zoneId}`, { method: "PUT", body: JSON.stringify({ [champ]: valeur }) });
};
window.supprimerZone = async (zoneId) => {
  if (!confirm("Supprimer cette zone ?")) return;
  await api(`/api/zones/${zoneId}`, { method: "DELETE" });
  chargerZones();
};

document.getElementById("btn-ajouter-zone").addEventListener("click", async () => {
  const body = {
    nom: document.getElementById("new-zone-nom").value.trim(),
    ville: document.getElementById("new-zone-ville").value.trim(),
    type_sol: document.getElementById("new-zone-sol").value,
    culture_specifique: document.getElementById("new-zone-culture").value,
    surface_hectares: Number(document.getElementById("new-zone-surface").value),
    humidite_sol: Number(document.getElementById("new-zone-humidite").value),
  };
  if (!body.nom || !body.ville) return alert("Nom et ville sont obligatoires.");
  await api("/api/zones", { method: "POST", body: JSON.stringify(body) });
  document.getElementById("new-zone-nom").value = "";
  document.getElementById("new-zone-ville").value = "";
  chargerZones();
});

// ---------- Réservoirs ----------
function majJauges(reservoirs) {
  for (const type of ["eau", "pesticide"]) {
    const r = reservoirs[type];
    const bar = document.getElementById(`gauge-${type}`);
    bar.style.width = `${Math.max(0, Math.min(100, r.niveau_pct))}%`;
    bar.style.background = r.niveau_pct > 40 ? "var(--success)" : r.niveau_pct > 20 ? "var(--warning)" : "var(--danger)";
    document.getElementById(`detail-${type}`).textContent =
      `${r.niveau_l.toFixed(0)} / ${r.capacite_l.toFixed(0)} L` + (r.niveau_pct <= 20 ? "  ⚠️ Niveau bas." : "");
  }
}
async function chargerReservoirs() { majJauges(await api("/api/reservoirs")); }

document.getElementById("btn-recharge-eau").addEventListener("click", async () => {
  await api("/api/reservoirs/eau/recharger", { method: "POST", body: JSON.stringify({ litres: Number(document.getElementById("recharge-eau-input").value) }) });
  chargerReservoirs();
});
document.getElementById("btn-recharge-pesticide").addEventListener("click", async () => {
  await api("/api/reservoirs/pesticide/recharger", { method: "POST", body: JSON.stringify({ litres: Number(document.getElementById("recharge-pesticide-input").value) }) });
  chargerReservoirs();
});

async function chargerEconomieEau() {
  document.getElementById("economie-eau").textContent = (await api("/api/economie-eau")).texte;
}

// ---------- Journal ----------
async function chargerJournal() {
  const items = await api("/api/journal");
  document.getElementById("journal-liste").textContent = items.length
    ? items.map((j) => `[${j.horodatage}] ${j.zone_nom} — ${j.action} : ${j.details}`).join("\n")
    : "Aucune action automatique pour le moment.";
}

// ---------- Utilisateurs (admin) ----------
async function chargerUsers() {
  const users = await api("/api/users");
  document.getElementById("liste-users").innerHTML = users.map((u) => `
    <div class="user-ligne">
      <span>${u.username} ${u.is_superuser ? "👑" : ""}</span>
      ${u.id !== MOI.id ? `<button class="btn-danger btn-small" onclick="supprimerUser(${u.id})">Supprimer</button>` : ""}
    </div>
  `).join("");
}
window.supprimerUser = async (id) => {
  if (!confirm("Supprimer cet utilisateur ?")) return;
  await api(`/api/users/${id}`, { method: "DELETE" });
  chargerUsers();
};
document.getElementById("btn-ajouter-user").addEventListener("click", async () => {
  const body = {
    username: document.getElementById("new-user-username").value.trim(),
    password: document.getElementById("new-user-password").value,
    is_superuser: document.getElementById("new-user-superuser").checked,
  };
  if (!body.username || !body.password) return alert("Nom d'utilisateur et mot de passe obligatoires.");
  try {
    await api("/api/users", { method: "POST", body: JSON.stringify(body) });
    document.getElementById("new-user-username").value = "";
    document.getElementById("new-user-password").value = "";
    chargerUsers();
  } catch (e) { alert(e.message); }
});

// ---------- Analyse : simulateur "et si..." ----------
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
    const data = await api("/api/comparer-scenarios", { method: "POST", body: JSON.stringify(body) });
    sortie.textContent = `🌡️ Actuel (${body.temp_base}°C) : ${data.scenario_actuel}\n\n🌡️ Hypothétique (${body.temp_hypothese}°C) : ${data.scenario_hypothese}`;
  } catch (e) { sortie.textContent = "❌ " + e.message; }
});
