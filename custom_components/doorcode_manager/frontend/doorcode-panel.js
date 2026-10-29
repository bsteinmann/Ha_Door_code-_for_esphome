/* Door Code Manager – sidebar panel. No build step; uses HA theme variables. */
const STATUS = { armed: "Bereit", code_accepted: "Akzeptiert", code_rejected: "Zugang abgelehnt", locked_out: "Gesperrt" };
const STATE = { active: "Aktiv", disabled: "Deaktiviert", used: "Verbraucht", expired: "Abgelaufen", scheduled: "Geplant" };
const RESULT = { granted: "Tür geöffnet", denied: "Abgelehnt", lockout: "Versuch während Sperre" };
const METHOD = { pin: "PIN", nfc: "NFC" };
const DOMAIN_LABEL = { script: "Skripte", scene: "Szenen", automation: "Automationen", button: "Buttons", input_button: "Buttons", switch: "Schalter", light: "Lichter", input_boolean: "Schalter (Helfer)", lock: "Schlösser", cover: "Rollläden/Tore" };

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pad = (n) => String(n).padStart(2, "0");
const toInput = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const toIso = (v) => (v ? new Date(v).toISOString() : null);

const CSS = `
:host{display:block;min-height:100vh;background:var(--primary-background-color);color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
*{box-sizing:border-box}
.bar{display:flex;align-items:center;gap:12px;height:56px;padding:0 16px;background:var(--app-header-background-color,var(--primary-color));color:var(--app-header-text-color,#fff)}
.bar h1{font-size:20px;font-weight:500;margin:0}
.grow{flex:1}
.wrap{max-width:1100px;margin:0 auto;padding:16px}
h2{font-size:16px;font-weight:500;margin:28px 0 8px}
button{font:inherit;cursor:pointer;border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--primary-text-color);border-radius:8px;padding:7px 12px}
button:hover{border-color:var(--primary-color)}
button:disabled{opacity:.6;cursor:default}
button:focus-visible,input:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}
.bar button{background:transparent;color:inherit;border-color:rgba(255,255,255,.55)}
.bar button.primary{background:#fff;color:var(--primary-color);border-color:#fff}
button.danger{color:var(--error-color)}
.chip{padding:3px 10px;border-radius:12px;font-size:13px;background:rgba(255,255,255,.2)}
.chip.locked_out{background:var(--error-color)}
.chip.code_accepted{background:var(--success-color,#43a047)}
.err{background:var(--error-color);color:#fff;padding:10px 14px;border-radius:8px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px}
.card{background:var(--card-background-color);border:1px solid var(--divider-color);border-left:4px solid var(--divider-color);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px}
.card.active{border-left-color:var(--success-color,#43a047)}
.card.scheduled{border-left-color:var(--info-color,#2196f3)}
.card.expired,.card.used{border-left-color:var(--warning-color,#ff9800)}
.top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.top b{font-size:16px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.badge{font-size:12px;padding:2px 8px;border-radius:10px;border:1px solid var(--divider-color);white-space:nowrap}
.code{display:flex;align-items:center;gap:8px;min-height:34px}
.code code{font-size:22px;letter-spacing:3px;font-variant-numeric:tabular-nums;flex:1}
.code button{padding:3px 9px;font-size:13px}
.muted{color:var(--secondary-text-color)}
.small{font-size:13px}
.acts{display:flex;align-items:center;gap:8px;margin-top:4px}
.acts label{flex:1;display:flex;align-items:center;gap:6px;cursor:pointer}
.hist .row{display:grid;grid-template-columns:150px 1fr auto;gap:10px;padding:7px 4px;border-bottom:1px solid var(--divider-color);font-size:14px}
.hist .row.denied span:last-child,.hist .row.lockout span:last-child{color:var(--error-color)}
dialog{border:none;border-radius:14px;padding:0;background:var(--card-background-color);color:var(--primary-text-color);width:min(480px,calc(100vw - 24px));max-height:calc(100vh - 24px)}
dialog::backdrop{background:rgba(0,0,0,.5)}
form{padding:20px;display:flex;flex-direction:column;gap:12px}
form h3{margin:0;font-size:18px;font-weight:500}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--divider-color)}
.tabs button{border:none;border-bottom:2px solid transparent;border-radius:0;background:transparent;padding:8px 12px}
.tabs button.on{border-bottom-color:var(--primary-color);color:var(--primary-color)}
.pane{display:flex;flex-direction:column;gap:12px;min-height:300px}
.pane[hidden]{display:none}
.f{display:flex;flex-direction:column;gap:6px;font-size:13px;color:var(--secondary-text-color)}
input[type=text],input[type=datetime-local]{font:inherit;padding:9px 10px;border-radius:8px;border:1px solid var(--divider-color);background:var(--primary-background-color);color:var(--primary-text-color)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.crow{display:flex;gap:8px}.crow input{flex:1}
.chk{display:flex;align-items:center;gap:8px;cursor:pointer;color:var(--primary-text-color);font-size:14px}
.tags{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.chip2{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--divider-color);border-radius:14px;padding:3px 4px 3px 10px;font-size:13px;color:var(--primary-text-color)}
.chip2 button{padding:0 8px;border:none;border-radius:10px;font-size:16px;line-height:1.5;background:transparent}
.list{display:flex;flex-direction:column;gap:6px;max-height:230px;overflow:auto;border:1px solid var(--divider-color);border-radius:8px;padding:8px}
.grp{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--secondary-text-color);margin-top:4px}
.grp:first-child{margin-top:0}
.derr{color:var(--error-color);font-size:14px;min-height:1em}
.btns{display:flex;justify-content:flex-end;gap:8px}
.btns .primary{background:var(--primary-color);color:#fff;border-color:var(--primary-color)}
.views{display:flex;gap:4px;margin-bottom:14px;border-bottom:1px solid var(--divider-color)}
.views button{border:none;border-bottom:3px solid transparent;border-radius:0;background:transparent;padding:10px 16px;font-size:15px}
.views button.on{border-bottom-color:var(--primary-color);color:var(--primary-color);font-weight:500}
@media(max-width:520px){.hist .row{grid-template-columns:1fr auto}.hist .row span:first-child{grid-column:1/-1}.two{grid-template-columns:1fr}}
`;

const HTML = `
<style>${CSS}</style>
<div class="bar">
  <ha-menu-button></ha-menu-button>
  <h1>Türcodes</h1><span id="chip" class="chip"></span><span class="grow"></span>
  <button id="once">Einmalcode</button><button id="new" class="primary">Neue Person</button>
</div>
<div class="wrap">
  <div class="views"><button type="button" data-view="person" class="on">Personen</button><button type="button" data-view="action">Aktionen</button></div>
  <div id="err" class="err" hidden></div>
  <div id="list" class="grid"></div>
  <h2>Verlauf</h2><div id="history" class="hist"></div>
</div>
<dialog id="dlg">
  <form id="form" novalidate>
    <h3 id="title"></h3>
    <div class="tabs" role="tablist">
      <button type="button" role="tab" data-tab="t1" class="on">Zugang</button>
      <button type="button" role="tab" data-tab="t2">Aktionen</button>
      <button type="button" role="tab" data-tab="t3">Benachrichtigung</button>
    </div>

    <div class="pane" data-pane="t1">
      <label class="f"><span id="namelbl">Name</span><input type="text" name="fname" maxlength="40" required placeholder="z. B. Max oder Reinigungskraft"></label>
      <label class="f">PIN-Code (optional, 4–12 Ziffern)
        <span class="crow"><input type="text" name="fcode" inputmode="numeric" autocomplete="off"><button type="button" id="gen">Zufällig</button></span>
      </label>
      <div class="f">NFC-Tags (optional)
        <div id="tags" class="tags"></div>
        <div><button type="button" id="learn">Tag anlernen</button></div>
      </div>
      <div class="two">
        <label class="f">Gültig ab<input type="datetime-local" name="ffrom"></label>
        <label class="f">Gültig bis<input type="datetime-local" name="funtil"></label>
      </div>
      <label class="chk"><input type="checkbox" name="fonce"> Einmalzugang: nach der ersten Nutzung ungültig</label>
      <label class="chk"><input type="checkbox" name="fenabled"> Aktiviert</label>
    </div>

    <div class="pane" data-pane="t2" hidden>
      <label class="chk" id="doorrow"><input type="checkbox" name="fdoor"> Tür öffnen</label>
      <div class="f">Zusätzlich auslösen
        <input type="text" id="actq" placeholder="Filtern …" autocomplete="off">
        <div id="acts" class="list"></div>
        <span id="acthint" class="small"></span>
      </div>
    </div>

    <div class="pane" data-pane="t3" hidden>
      <label class="chk"><input type="checkbox" name="fnotify"> Benachrichtigung bei Nutzung</label>
      <div id="tbox" class="f">Empfänger (Geräte mit Companion-App)
        <div id="targets" class="list"></div>
        <span class="small">Ohne Auswahl gelten die Standard-Empfänger aus den Integrations-Optionen.</span>
      </div>
    </div>

    <div id="derr" class="derr"></div>
    <div class="btns"><button type="button" id="cancel">Abbrechen</button><button type="submit" class="primary">Speichern</button></div>
  </form>
</dialog>`;

class DoorcodePanel extends HTMLElement {
  constructor() {
    super();
    this._r = this.attachShadow({ mode: "open" });
    this._r.innerHTML = HTML;
    this._data = { codes: [], history: [], status: "armed" };
    this._reveal = new Set();
    this._editing = null;
    this._view = "person";
    this._kind = "person";
    this._tags = [];
    this._cur = { actions: [], targets: [] };
    this._loaded = { actions: false, targets: false };
    this._unsub = null;
    this._subscribing = false;

    const $ = (s) => this._r.querySelector(s);
    this._dlg = $("#dlg");
    $("#new").onclick = () => this._open(null);
    $("#once").onclick = () => this._open(null, { kind: "person", name: "Einmalcode", code: this._gen(), one_time: true, expires_at: new Date(Date.now() + 864e5).toISOString() });
    $("#gen").onclick = () => { this._form().fcode.value = this._gen(); };
    $("#learn").onclick = () => this._learn();
    this._r.querySelectorAll(".views button").forEach((b) => { b.onclick = () => { this._view = b.dataset.view; this._viewUI(); this._render(); }; });
    this._viewUI();
    $("#cancel").onclick = () => this._dlg.close();
    $("#form").onsubmit = (e) => this._save(e);
    $("#form").elements.fnotify.onchange = () => this._tbox();
    $("#actq").oninput = () => this._filterActions();
    this._r.querySelectorAll(".tabs button").forEach((b) => { b.onclick = () => this._tab(b.dataset.tab); });
    $("#tags").addEventListener("click", (e) => {
      const b = e.target.closest("[data-rm]");
      if (b) { this._tags.splice(Number(b.dataset.rm), 1); this._renderTags(); }
    });
    this._dlg.addEventListener("close", () => { this._call("cancel_learn").catch(() => {}); });
    $("#list").addEventListener("click", (e) => this._act(e));
    $("#list").addEventListener("change", (e) => this._act(e));
  }

  set hass(h) { this._hass = h; this._menu(); this._ensure(); }
  set narrow(v) { this._narrow = v; this._menu(); }
  connectedCallback() { this._ensure(); }
  disconnectedCallback() { if (this._unsub) { this._unsub(); this._unsub = null; } }

  _menu() {
    const m = this._r.querySelector("ha-menu-button");
    if (m) { m.hass = this._hass; m.narrow = this._narrow; }
  }

  async _ensure() {
    if (!this._hass || this._unsub || this._subscribing) return;
    this._subscribing = true;
    try {
      this._unsub = await this._hass.connection.subscribeMessage(
        (d) => { this._data = d; this._render(); },
        { type: "doorcode_manager/subscribe" }
      );
      this._showErr("");
    } catch (e) {
      this._showErr("Verbindung fehlgeschlagen: " + (e.message || e) + " – ist die Integration eingerichtet und bist du Administrator?");
    }
    this._subscribing = false;
  }

  _form() { return this._r.querySelector("#form").elements; }
  _gen() { const a = new Uint32Array(1); crypto.getRandomValues(a); return String(a[0] % 1000000).padStart(6, "0"); }
  _fmt(iso) { return new Date(iso).toLocaleString(this._hass?.locale?.language || "de", { dateStyle: "short", timeStyle: "short" }); }
  _showErr(msg) { const e = this._r.querySelector("#err"); e.textContent = msg; e.hidden = !msg; }
  _call(cmd, data) { return this._hass.callWS({ type: `doorcode_manager/${cmd}`, ...data }); }

  _render() {
    const d = this._data;
    const chip = this._r.querySelector("#chip");
    chip.textContent = STATUS[d.status] || d.status;
    chip.className = "chip " + d.status;
    const kindOf = (c) => c.kind || "person";
    const n = { person: d.codes.filter((c) => kindOf(c) === "person").length, action: d.codes.filter((c) => kindOf(c) === "action").length };
    this._r.querySelectorAll(".views button").forEach((b) => { b.textContent = `${b.dataset.view === "person" ? "Personen" : "Aktionen"} (${n[b.dataset.view]})`; });
    const shown = d.codes.filter((c) => kindOf(c) === this._view);
    this._r.querySelector("#list").innerHTML = shown.length
      ? shown.map((c) => this._card(c)).join("")
      : (this._view === "action"
        ? '<p class="muted">Noch keine Aktionen. Lege mit „Neue Aktion“ z. B. „Alarm scharf“ oder „Alle Lichter aus“ an.</p>'
        : '<p class="muted">Noch keine Personen. Lege mit „Neue Person“ die erste an.</p>');
    this._r.querySelector("#history").innerHTML = d.history.length
      ? d.history.map((h) => `<div class="row ${esc(h.result)}"><span class="muted">${esc(this._fmt(h.time))}</span><b>${esc(h.name || "–")}</b><span>${esc(h.result === "granted" && h.kind === "action" ? "Aktion ausgelöst" : (RESULT[h.result] || h.result))}${h.method ? " · " + esc(METHOD[h.method] || h.method) : ""}</span></div>`).join("")
      : '<p class="muted">Noch keine Zugriffe.</p>';
  }

  _card(c) {
    const id = esc(c.id);
    const tags = c.tags || [];
    const meta = [];
    if (tags.length) meta.push(`NFC ×${tags.length}`);
    if ((c.actions || []).length) meta.push(`Aktionen ×${c.actions.length}`);
    if (c.open_door === false && (c.kind || "person") !== "action") meta.push("ohne Türöffnung");
    if (c.one_time) meta.push("Einmalzugang");
    if (c.valid_from) meta.push("ab " + this._fmt(c.valid_from));
    if (c.expires_at) meta.push("bis " + this._fmt(c.expires_at));
    const shown = c.code ? (this._reveal.has(c.id) ? c.code : "•".repeat(c.code.length)) : "";
    const codeRow = c.code
      ? `<div class="code"><code>${esc(shown)}</code><button data-a="reveal" data-id="${id}">${this._reveal.has(c.id) ? "Verbergen" : "Anzeigen"}</button></div>`
      : `<div class="code muted">Kein PIN – nur NFC</div>`;
    return `<div class="card ${esc(c.status)}">
      <div class="top"><b>${esc(c.name)}</b><span class="badge">${esc(STATE[c.status] || c.status)}</span></div>
      ${codeRow}
      <div class="muted small">${esc(meta.join(" · ") || "Dauerhaft gültig")}</div>
      <div class="muted small">${c.use_count}× genutzt${c.last_used ? ", zuletzt " + esc(this._fmt(c.last_used)) : ""} · ID ${id}</div>
      <div class="acts">
        <label><input type="checkbox" data-a="toggle" data-id="${id}" ${c.enabled && !c.used ? "checked" : ""}> Aktiv</label>
        <button data-a="edit" data-id="${id}">Bearbeiten</button>
        <button class="danger" data-a="delete" data-id="${id}">Löschen</button>
      </div></div>`;
  }

  async _act(e) {
    const el = e.target.closest("[data-a]");
    if (!el) return;
    const isInput = el.tagName === "INPUT";
    if ((e.type === "click" && isInput) || (e.type === "change" && !isInput)) return;
    const id = el.dataset.id;
    const c = this._data.codes.find((x) => x.id === id);
    try {
      this._showErr("");
      switch (el.dataset.a) {
        case "reveal": this._reveal.has(id) ? this._reveal.delete(id) : this._reveal.add(id); this._render(); break;
        case "edit": if (c) this._open(c); break;
        case "delete": if (c && confirm(`„${c.name}“ wirklich löschen?`)) await this._call("delete", { code_id: id }); break;
        case "toggle": await this._call("update", { code_id: id, enabled: el.checked }); break;
      }
    } catch (err) {
      this._showErr(err.message || String(err));
      this._render();
    }
  }

  _viewUI() {
    this._r.querySelectorAll(".views button").forEach((b) => b.classList.toggle("on", b.dataset.view === this._view));
    this._r.querySelector("#new").textContent = this._view === "action" ? "Neue Aktion" : "Neue Person";
    this._r.querySelector("#once").style.display = this._view === "action" ? "none" : "";
  }

  // ---------- dialog ----------
  _tab(name) {
    this._r.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
    this._r.querySelectorAll(".pane").forEach((p) => { p.hidden = p.dataset.pane !== name; });
  }

  _renderTags() {
    this._r.querySelector("#tags").innerHTML = this._tags.length
      ? this._tags.map((t, i) => `<span class="chip2" title="${esc(t)}">Tag ${i + 1} · …${esc(t.slice(-5))}<button type="button" data-rm="${i}" aria-label="Tag entfernen">×</button></span>`).join("")
      : '<span class="muted small">Noch kein Tag zugeordnet</span>';
  }

  _tbox() { this._r.querySelector("#tbox").style.display = this._form().fnotify.checked ? "" : "none"; }

  async _loadTargets(selected) {
    const box = this._r.querySelector("#targets");
    this._loaded.targets = false;
    box.innerHTML = '<span class="muted small">Lade …</span>';
    try {
      const list = await this._call("notify_targets");
      const known = new Set(list.map((t) => t.service));
      const all = [...list, ...selected.filter((s) => !known.has(s)).map((s) => ({ service: s, label: `${s} (nicht gefunden)` }))];
      box.innerHTML = all.length
        ? all.map((t) => `<label class="chk"><input type="checkbox" name="tgt" value="${esc(t.service)}" ${selected.includes(t.service) ? "checked" : ""}> ${esc(t.label)}</label>`).join("")
        : '<span class="muted small">Keine Geräte mit Companion-App gefunden.</span>';
      this._loaded.targets = true;
    } catch (e) {
      box.innerHTML = `<span class="muted small">${esc(e.message || e)}</span>`;
    }
  }

  async _loadActions(selected) {
    const box = this._r.querySelector("#acts");
    const hint = this._r.querySelector("#acthint");
    this._loaded.actions = false;
    this._r.querySelector("#actq").value = "";
    hint.textContent = "";
    box.innerHTML = '<span class="muted small">Lade …</span>';
    try {
      const res = await this._call("action_entities");
      const st = this._hass?.states || {};
      const known = new Set(res.entities.map((e) => e.entity_id));
      const extra = selected.filter((s) => !known.has(s)).map((s) => ({ entity_id: s, name: `${st[s]?.attributes?.friendly_name || s} (ohne Label)`, domain: s.split(".")[0] }));
      const all = [...res.entities, ...extra];
      const groups = {};
      all.forEach((e) => { (groups[DOMAIN_LABEL[e.domain] || e.domain] ||= []).push(e); });
      box.innerHTML = all.length
        ? Object.entries(groups).map(([g, items]) => `<div class="grp">${esc(g)}</div>` + items.map((e) => `<label class="chk" data-q="${esc((e.name + " " + e.entity_id).toLowerCase())}"><input type="checkbox" name="act" value="${esc(e.entity_id)}" ${selected.includes(e.entity_id) ? "checked" : ""}> ${esc(e.name)}</label>`).join("")).join("")
        : '<span class="muted small">Keine Entitäten gefunden.</span>';
      if (!res.label) hint.textContent = "Noch kein Label festgelegt: Integrations-Optionen → „Label für wählbare Aktionen“. Danach Skripten, Szenen usw. dieses Label geben.";
      else if (!res.entities.length) hint.textContent = `Keine Entität mit dem Label „${res.label}“ gefunden.`;
      else hint.textContent = `Angezeigt werden nur Entitäten mit dem Label „${res.label}“.`;
      this._loaded.actions = true;
    } catch (e) {
      box.innerHTML = `<span class="muted small">${esc(e.message || e)}</span>`;
    }
  }

  _filterActions() {
    const q = this._r.querySelector("#actq").value.trim().toLowerCase();
    this._r.querySelectorAll("#acts label").forEach((l) => { l.style.display = !q || l.dataset.q.includes(q) ? "" : "none"; });
  }

  async _learn() {
    const b = this._r.querySelector("#learn");
    const derr = this._r.querySelector("#derr");
    derr.textContent = "";
    b.disabled = true;
    b.textContent = "Halte den Tag an den Leser … (30 s)";
    try {
      const r = await this._call("learn_tag");
      if (!this._tags.some((t) => t.toLowerCase() === r.tag_id.toLowerCase())) this._tags.push(r.tag_id);
      this._renderTags();
    } catch (e) {
      derr.textContent = e.message || String(e);
    }
    b.disabled = false;
    b.textContent = "Tag anlernen";
  }

  _open(c, preset = {}) {
    this._editing = c ? c.id : null;
    const v = c || { name: "", code: "", tags: [], enabled: true, one_time: false, notify: true, notify_targets: [], open_door: true, actions: [], valid_from: null, expires_at: null, ...preset };
    const f = this._form();
    this._kind = c ? (c.kind || "person") : (preset.kind || this._view);
    const isAct = this._kind === "action";
    this._r.querySelector("#title").textContent = c ? (isAct ? "Aktion bearbeiten" : "Person bearbeiten") : (isAct ? "Neue Aktion" : "Neue Person");
    this._r.querySelector("#namelbl").textContent = isAct ? "Name der Aktion" : "Name der Person";
    f.fname.placeholder = isAct ? "z. B. Alarm scharf oder Alles aus" : "z. B. Max oder Reinigungskraft";
    this._r.querySelector('[data-tab="t1"]').textContent = isAct ? "Auslöser" : "Zugang";
    this._r.querySelector("#doorrow").style.display = isAct ? "none" : "";
    f.fname.value = v.name;
    f.fcode.value = v.code || "";
    f.ffrom.value = toInput(v.valid_from);
    f.funtil.value = toInput(v.expires_at);
    f.fonce.checked = !!v.one_time;
    f.fnotify.checked = v.notify !== false;
    f.fenabled.checked = v.enabled !== false;
    f.fdoor.checked = isAct ? false : v.open_door !== false;
    this._tags = [...(v.tags || [])];
    this._cur = { actions: [...(v.actions || [])], targets: [...(v.notify_targets || [])] };
    this._renderTags();
    this._tbox();
    this._tab("t1");
    this._loadTargets(this._cur.targets);
    this._loadActions(this._cur.actions);
    this._r.querySelector("#derr").textContent = "";
    this._dlg.showModal();
  }

  async _save(e) {
    e.preventDefault();
    const f = this._form();
    const derr = this._r.querySelector("#derr");
    const fail = (tab, msg) => { this._tab(tab); derr.textContent = msg; };
    const name = f.fname.value.trim();
    const code = f.fcode.value.trim();
    if (!name) return fail("t1", "Bitte einen Namen eingeben.");
    if (code && !/^[0-9]{4,12}$/.test(code)) return fail("t1", "Der PIN muss aus 4 bis 12 Ziffern bestehen.");
    if (!code && !this._tags.length) return fail("t1", "Bitte einen PIN oder mindestens einen NFC-Tag angeben.");
    // if a list failed to load, keep what was stored instead of silently dropping it
    const checked = (n) => [...this._r.querySelectorAll(`input[name="${n}"]:checked`)].map((i) => i.value);
    const actions = this._loaded.actions ? checked("act") : this._cur.actions;
    const targets = this._loaded.targets ? checked("tgt") : this._cur.targets;
    if (!f.fdoor.checked && !actions.length) return fail("t2", this._kind === "action" ? "Bitte mindestens eine Aktion wählen." : "Bitte „Tür öffnen“ aktivieren oder mindestens eine Aktion wählen.");
    const data = {
      kind: this._kind, name, code: code || null, tags: this._tags, open_door: f.fdoor.checked, actions,
      one_time: f.fonce.checked, notify: f.fnotify.checked, notify_targets: targets,
      enabled: f.fenabled.checked, valid_from: toIso(f.ffrom.value), expires_at: toIso(f.funtil.value),
    };
    try {
      if (this._editing) await this._call("update", { code_id: this._editing, ...data });
      else await this._call("add", data);
      this._dlg.close();
    } catch (err) {
      derr.textContent = err.message || String(err);
    }
  }
}

customElements.define("doorcode-panel", DoorcodePanel);
