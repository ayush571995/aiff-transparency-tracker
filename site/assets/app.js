// Shared helpers for every page. No framework, no build step — this file is
// fetched directly by the browser. Every render function that shows a claim
// also renders the source link(s) it came from; nothing appears unsourced.

const DATA = {
  base: "data/",
  async json(name) {
    const res = await fetch(`${this.base}${name}?v=${Date.now() % 100000}`, { cache: "no-cache" });
    if (!res.ok) throw new Error(`Failed to load ${name}: HTTP ${res.status}`);
    return res.json();
  },
};

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtDate(iso) {
  if (!iso) return "date unknown";
  try {
    const d = new Date(iso);
    if (isNaN(d)) return escapeHtml(iso);
    return d.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return escapeHtml(iso);
  }
}

function statusPillClass(status) {
  if (!status) return "";
  const s = status.toLowerCase();
  if (s.includes("disputed") || s.includes("allegation") || s.includes("denied")) return "status-disputed";
  return "";
}

async function loadManifest(targetSelector) {
  const el = document.querySelector(targetSelector);
  if (!el) return;
  try {
    const m = await DATA.json("manifest.json");
    el.innerHTML = `<span class="dot"></span> Documents/news last pulled from AIFF's own site: <strong>${fmtDate(m.last_updated)}</strong> (${m.last_updated} UTC) &middot; ${m.counts.documents} documents &middot; ${m.counts.news} news items indexed`;
  } catch (e) {
    el.textContent = "Could not load last-updated info.";
  }
}

function setActiveNav() {
  const path = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav.site a").forEach((a) => {
    if (a.getAttribute("href") === path) a.classList.add("active");
  });
}

// Apply theme override from viewer preference if the host sets data-theme on <html>.
(function () {
  try {
    const saved = localStorage.getItem("theme-override");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch {}
})();

document.addEventListener("DOMContentLoaded", setActiveNav);
