/* AgriVerse dashboard data layer.
 *
 * The HTML/CSS remain the reviewed visual baseline; this file replaces the
 * static demo values with the device API, keeps an honest offline state and
 * never renders a value that did not come from /api/v1/state.
 */
(() => {
  "use strict";

  const API = "/api/v1";
  const POLL_MS = 2000;
  const MAX_BACKOFF_MS = 30000;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const VIEW_LABELS = {
    overview: "总览仪表盘",
    environment: "环境监测",
    irrigation: "灌溉管理",
    calendar: "节气与种植",
    device: "设备管理",
    settings: "系统设置"
  };

  const PLANT_NAMES = {
    general: "通用",
    lettuce: "生菜",
    tomato: "番茄",
    strawberry: "草莓"
  };

  const PLANT_STAGE_NAMES = {
    seedling: "苗期",
    growth: "生长期",
    flowering: "开花结果期",
    harvest: "成熟采收期"
  };

  const PLANT_METRICS = [
    ["soil", "土壤"],
    ["temp", "温度"],
    ["humidity", "湿度"],
    ["light", "光照"]
  ];

  const HABIT_LABELS = {
    upright: "直立",
    bush: "丛生/灌木",
    vining: "蔓生",
    climbing: "攀援",
    rosette: "莲座"
  };
  const LIFE_LABELS = { annual: "一年生", biennial: "二年生", perennial: "多年生" };
  const ROOT_LABELS = { taproot: "直根系", fibrous: "须根系", adventitious: "不定根" };
  const PHOTOPERIOD_LABELS = { short_day: "短日照", long_day: "长日照", day_neutral: "日中性" };
  const SENSITIVITY_LABELS = { low: "低", medium: "中", high: "高" };
  const POLLINATION_LABELS = {
    self: "自花授粉",
    wind: "风媒",
    insect: "虫媒",
    self_or_insect: "自花/虫媒"
  };
  const SUPPORT_LABELS = { none: "不需要", stake: "支柱", trellis: "棚架", cage: "笼架" };

  const state = {
    data: null,
    online: false,
    backoff: POLL_MS,
    pin: readPin(),
    timeSyncing: false,
    terms: null,
    termsAt: 0,
    selectedTerm: null,
    termTouched: false,
    history: null,
    historyAt: 0,
    historyRange: "12h",
    chartBusy: false,
    calibrationDraft: null,
    currentView: "overview",
    settingsKey: null,
    plantProfiles: null,
    pollTimer: null,
    modal: null,
    pinPromise: null
  };

  let toastTimer = null;

  // ------------------------------------------------------------------ utils
  function readPin() {
    try {
      return localStorage.getItem("agri_pin") || "";
    } catch (_error) {
      return "";
    }
  }

  function storePin(pin) {
    try {
      if (pin) localStorage.setItem("agri_pin", pin);
      else localStorage.removeItem("agri_pin");
    } catch (_error) {
      /* private mode: keep it in memory only */
    }
  }

  function notify(message) {
    const toast = $("#toast");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
  }

  function num(value, digits = 0) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    const number = Number(value);
    if (digits > 0) return number.toFixed(digits);
    return Math.round(number).toLocaleString("zh-CN");
  }

  function timeText(ts) {
    if (!ts) return "—";
    try {
      return new Date(ts * 1000).toLocaleString("zh-CN", { hour12: false });
    } catch (_error) {
      return "—";
    }
  }

  function shortTime(ts) {
    if (!ts) return "—";
    try {
      return new Date(ts * 1000).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    } catch (_error) {
      return "—";
    }
  }

  function uptimeText(seconds) {
    let total = Math.max(0, Number(seconds) || 0);
    const days = Math.floor(total / 86400);
    total %= 86400;
    const hours = Math.floor(total / 3600);
    total %= 3600;
    const minutes = Math.floor(total / 60);
    if (days) return `${days} 天 ${hours} 小时`;
    if (hours) return `${hours} 小时 ${minutes} 分`;
    return `${minutes} 分`;
  }

  function make(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function field(label, value) {
    const box = make("div", "agri-field");
    box.appendChild(make("div", "stat-foot", label));
    box.appendChild(make("strong", "", value));
    return box;
  }

  function reading(name) {
    return state.data && state.data.sensors ? state.data.sensors[name] : null;
  }

  function statusOf(sensor) {
    if (!sensor) return "无数据";
    if (!sensor.valid) return sensor.error === "uncalibrated" ? "未标定" : "异常";
    const now = (state.data && state.data.meta && state.data.meta.ts) || Math.floor(Date.now() / 1000);
    if (now - Number(sensor.ts || 0) > 90) return "数据过期";
    return "在线";
  }

  function statusColor(status) {
    if (status === "在线") return "var(--green2)";
    if (status === "未标定" || status === "数据过期") return "var(--gold)";
    return "var(--red)";
  }

  function navTo(name) {
    if (!VIEW_LABELS[name]) return;
    state.currentView = name;
    $$(".view").forEach((view) => view.classList.toggle("active", view.id === name));
    $$(".nav button[data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === name));
    const crumb = $("#crumbName");
    if (crumb) crumb.textContent = VIEW_LABELS[name];
    const sidebar = $("#sidebar");
    if (sidebar) sidebar.classList.remove("open");
    window.scrollTo(0, 0);
    setTimeout(() => window.scrollTo(0, 0), 40);
    try {
      if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
    } catch (_error) {
      /* file:// or restricted context: deep links are optional */
    }

    if (name === "overview") {
      renderOverview();
      fetchHistory();
    } else if (name === "environment") {
      renderEnvironment();
    } else if (name === "irrigation") {
      renderIrrigation();
    } else if (name === "calendar") {
      state.termTouched = false;
      fetchTerms();
      renderCalendar();
    } else if (name === "device") {
      renderDevice();
    } else if (name === "settings") {
      fetchPlantProfiles();
      renderSettings(true);
    }
  }

  // -------------------------------------------------------------------- PIN
  function askPin(message) {
    if (state.pinPromise) return state.pinPromise;
    state.pinPromise = new Promise((resolve) => {
      const overlay = make("div", "agri-modal");
      const card = make("div", "agri-modal-card");
      card.appendChild(make("h3", "", "需要设备 PIN"));
      card.appendChild(make("p", "agri-muted", message || "请输入设备屏幕或设置页显示的 6 位 PIN。"));
      const input = make("input", "agri-input");
      input.type = "password";
      input.inputMode = "numeric";
      input.maxLength = 6;
      input.placeholder = "6 位数字";
      card.appendChild(input);
      const error = make("div", "agri-error");
      card.appendChild(error);
      const actions = make("div", "agri-modal-actions");
      const cancel = make("button", "btn", "取消");
      const submit = make("button", "btn agri-primary", "确认");
      cancel.type = "button";
      submit.type = "button";
      actions.appendChild(cancel);
      actions.appendChild(submit);
      card.appendChild(actions);
      overlay.appendChild(card);
      document.body.appendChild(overlay);
      state.modal = overlay;
      setTimeout(() => input.focus(), 30);

      function close(value) {
        if (state.modal === overlay) state.modal = null;
        state.pinPromise = null;
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        resolve(value);
      }

      function accept() {
        const value = input.value.trim();
        if (!/^\d{6}$/.test(value)) {
          error.textContent = "请输入 6 位数字 PIN";
          return;
        }
        storePin(value);
        close(value);
      }

      submit.addEventListener("click", accept);
      cancel.addEventListener("click", () => close(""));
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") accept();
        else if (event.key === "Escape") close("");
      });
    });
  }

  // -------------------------------------------------------------------- API
  class ApiError extends Error {
    constructor(code, message, status) {
      super(message || "请求失败");
      this.code = code;
      this.status = status || 0;
    }
  }

  async function api(path, options = {}, retried = false) {
    const controller = new AbortController();
    const timeout = options.timeout || 3000;
    const timer = setTimeout(() => controller.abort(), timeout);
    const headers = { "Content-Type": "application/json" };
    if (state.pin) headers["X-AgriVerse-Pin"] = state.pin;
    try {
      const response = await fetch(API + path, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
        cache: "no-store"
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch (_error) {
        payload = null;
      }
      if (response.status === 401 && payload && payload.error) {
        if (retried) throw new ApiError(payload.error.code, payload.error.message, 401);
        const pin = await askPin(payload.error.message);
        if (!pin) throw new ApiError("PIN_CANCELLED", "已取消 PIN 输入", 401);
        state.pin = pin;
        return api(path, options, true);
      }
      if (!response.ok || !payload || !payload.ok) {
        const error = (payload && payload.error) || {};
        throw new ApiError(error.code || `HTTP_${response.status}`, error.message || "设备返回错误", response.status);
      }
      return payload.data;
    } catch (error) {
      if (error.name === "AbortError") throw new ApiError("TIMEOUT", "设备响应超时", 0);
      if (error instanceof ApiError) throw error;
      throw new ApiError("NETWORK", "无法连接设备", 0);
    } finally {
      clearTimeout(timer);
    }
  }

  // ------------------------------------------------------------------ state
  function schedule(delay) {
    clearTimeout(state.pollTimer);
    if (document.hidden) return;
    state.pollTimer = setTimeout(fetchState, delay);
  }

  async function fetchState() {
    try {
      const data = await api("/state");
      state.data = data;
      state.online = true;
      state.backoff = POLL_MS;
      renderAll();
      setBanner();
      maybeSyncTime(data);
      schedule(POLL_MS);
    } catch (error) {
      state.online = false;
      updateChrome();
      setBanner(error && error.message);
      state.backoff = Math.min(Math.round(state.backoff * 1.7), MAX_BACKOFF_MS);
      schedule(state.backoff);
    }
  }

  function maybeSyncTime(data) {
    if (!data || !data.device || data.device.time_synced !== false) return;
    if (!data.meta || data.meta.source === "simulator") return;
    if (state.timeSyncing) return;
    state.timeSyncing = true;
    api("/time", { method: "POST", body: { epoch: Math.floor(Date.now() / 1000) } })
      .catch(() => null)
      .finally(() => {
        state.timeSyncing = false;
      });
  }

  async function fetchHistory() {
    if (state.chartBusy) return;
    state.chartBusy = true;
    try {
      const data = await api(`/history?range=${encodeURIComponent(state.historyRange)}`);
      state.history = data.points || [];
      state.historyAt = Date.now();
      renderChart();
    } catch (_error) {
      /* the offline banner already explains the failure */
    } finally {
      state.chartBusy = false;
    }
  }

  async function fetchTerms(force = false) {
    if (!force && state.terms && Date.now() - state.termsAt < 3600000) return;
    try {
      const data = await api("/solar-terms");
      state.terms = data.terms || [];
      state.termsAt = Date.now();
      populateSeasonSelect();
      if (state.currentView === "overview") renderOverviewSolar();
      if (state.currentView === "calendar") renderCalendar();
    } catch (_error) {
      /* keep the current content; the banner shows offline */
    }
  }

  async function fetchPlantProfiles(force = false) {
    if (!force && state.plantProfiles) return;
    try {
      const data = await api("/plant-profiles");
      state.plantProfiles = data.profiles || [];
      if (state.currentView === "settings") renderSettings(true);
    } catch (_error) {
      /* built-in profile names remain available */
    }
  }

  // ----------------------------------------------------------------- render
  function renderAll() {
    renderOverview();
    renderEnvironment();
    renderIrrigation();
    if (state.currentView === "calendar") renderCalendar();
    if (state.currentView === "device") renderDevice();
    if (state.currentView === "settings") renderSettings(false);
    updateChrome();
  }

  function renderOverview() {
    if (!state.data) return;
    const temp = reading("air_temp");
    const humidity = reading("air_humidity");
    const soil = reading("soil");
    const light = reading("light");

    setStatCards("#overview", [
      { value: temp, unit: "°C", digits: 1, label: "SHT31" },
      { value: humidity, unit: "%", digits: 0, label: "SHT31" },
      { value: soil, unit: "%", digits: 0, label: "电容式传感器" },
      { value: light, unit: "lx", digits: 0, label: "BH1750" }
    ]);

    renderOverviewSolar();
    renderPump();
    renderScore();
    const sub = $(".chart-card .card-sub");
    if (sub) sub.textContent = "传感器历史数据 · 实时";
    if (!state.history || Date.now() - state.historyAt > 60000) fetchHistory();
    else renderChart();
  }

  function renderOverviewSolar() {
    const tipsBox = $("#overviewSolarTips");
    const nextBox = $("#overviewSolarNext");
    if (!tipsBox) return;
    const current = state.data && state.data.solar_term ? state.data.solar_term : null;
    const terms = state.terms || [];
    const currentName = current && current.name && current.name !== "—" ? current.name : "";
    const term = currentName ? termByName(currentName) || current : null;
    const sub = $("#overviewSolarSub");
    const nameNode = $("#overviewSolarName");
    const seasonNode = $("#overviewSolarSeason");
    const dateNode = $("#overviewSolarDate");
    const now = state.data && state.data.device ? Number(state.data.device.now) : 0;
    const endTs = Number((current && current.end_ts) || (term && term.end_ts) || 0);
    let daysLeft = null;
    if (endTs && now) {
      const remaining = (endTs - now) / 86400;
      if (Number.isFinite(remaining)) daysLeft = Math.max(0, Math.ceil(remaining));
    }
    if (sub) sub.textContent = term ? `当前：${term.name}${term.season ? ` · ${term.season}` : ""}` : "当前：等待设备校时";
    if (nameNode) nameNode.textContent = term ? term.name : "—";
    if (seasonNode) {
      const index = Number(term && term.index);
      seasonNode.textContent = term
        ? `${term.season || "—"}${Number.isFinite(index) ? ` · 第 ${index + 1} 个节气` : ""}${daysLeft === null ? "" : ` · 本节气还剩 ${daysLeft} 天`}`
        : "—";
    }
    if (dateNode) {
      dateNode.textContent = term
        ? (term.date_hint ? `通常在 ${term.date_hint} 前后` : `太阳黄经约 ${term.angle}°`)
        : "—";
    }

    tipsBox.textContent = "";
    const tips = term && Array.isArray(term.tips) ? term.tips : [];
    if (tips.length) {
      tips.forEach((item) => {
        const box = make("div", "solar-tip");
        box.appendChild(make("b", "", item[0]));
        box.appendChild(make("p", "", item[1]));
        tipsBox.appendChild(box);
      });
    } else if (term) {
      const box = make("div", "solar-tip solar-tip-empty");
      box.appendChild(make("b", "", "农事建议待补充"));
      box.appendChild(make("p", "", term.intro || "该节气的农事内容暂未收录。"));
      tipsBox.appendChild(box);
    } else {
      tipsBox.appendChild(make("div", "solar-tip solar-tip-empty", "设备时间同步后显示当前节气农事。"));
    }

    if (nextBox) {
      nextBox.textContent = "";
      if (term && terms.length) {
        const index = Number(term.index);
        const next = terms[(Number.isFinite(index) ? index + 1 : 0) % terms.length];
        nextBox.appendChild(make("b", "", "下一个节气："));
        nextBox.appendChild(document.createTextNode(`${next.name}${next.date_hint ? ` · ${next.date_hint}` : ""}`));
      } else {
        nextBox.appendChild(document.createTextNode("查看完整二十四节气农事 →"));
      }
    }
    renderPlantProfile();
  }

  function traitLabel(value, labels) {
    if (value === undefined || value === null || value === "") return "";
    return labels[value] || String(value);
  }

  function rangeText(value, unit) {
    if (!Array.isArray(value) || value.length !== 2) return "";
    return `${value[0]}–${value[1]}${unit || ""}`;
  }

  function renderPlantProfile() {
    const suit = (state.data && state.data.suitability) || {};
    const traits = suit.traits || {};
    const stageInfo = suit.stage_info || {};
    const profileName = suit.profile_name || "";
    const stageName = suit.stage_name || "";
    const line = $("#overviewPlantLine");
    if (line) {
      if (!profileName) {
        line.textContent = "";
      } else {
        const bits = [`当前作物：${profileName} · ${stageName}`];
        if (traits.plant_habit) bits.push(`株型：${traitLabel(traits.plant_habit, HABIT_LABELS)}`);
        if (typeof traits.root_depth_cm === "number") bits.push(`根深约 ${traits.root_depth_cm} cm`);
        if (traits.pollination) bits.push(`授粉：${traitLabel(traits.pollination, POLLINATION_LABELS)}`);
        line.textContent = bits.join(" · ");
      }
    }

    const panel = $("#plantProfilePanel");
    if (!panel) return;
    const sub = $("#plantProfileSub");
    const grid = $("#plantTraits");
    const note = $("#plantStageNote");
    if (!grid) return;
    if (!profileName) {
      if (sub) sub.textContent = "等待作物档案";
      grid.textContent = "";
      if (note) note.textContent = "设备上报作物档案后显示。";
      return;
    }
    if (sub) {
      const review = traits.control_eligible === true ? "已审核" : "档案参考";
      sub.textContent = `${profileName} · ${stageName} · ${review}`;
    }
    grid.textContent = "";
    const add = (label, value) => {
      if (value === undefined || value === null || value === "" || (Array.isArray(value) && !value.length)) return;
      const box = make("div", "plant-trait");
      box.appendChild(make("small", "", label));
      box.appendChild(make("strong", "", Array.isArray(value) ? value.join("、") : String(value)));
      grid.appendChild(box);
    };
    if (!Object.keys(traits).length) {
      grid.appendChild(make("div", "agri-muted", "该档案未提供扩展特性。可在设置中导入包含 traits 的 JSON。"));
    } else {
      add("株型", traitLabel(traits.plant_habit, HABIT_LABELS));
      add("生命周期", traitLabel(traits.lifecycle, LIFE_LABELS));
      add("根系", traitLabel(traits.root_type, ROOT_LABELS));
      add("根深", typeof traits.root_depth_cm === "number" ? `${traits.root_depth_cm} cm` : "");
      add("株高", typeof traits.mature_height_cm === "number" ? `${traits.mature_height_cm} cm` : "");
      add("株距", typeof traits.spacing_cm === "number" ? `${traits.spacing_cm} cm` : "");
      add("支撑", traitLabel(traits.support, SUPPORT_LABELS));
      add("修剪", traits.pruning);
      add("授粉", traitLabel(traits.pollination, POLLINATION_LABELS));
      add("光周期", `${traitLabel(traits.photoperiod_type, PHOTOPERIOD_LABELS)}${typeof traits.critical_daylength_h === "number" ? ` · 临界 ${traits.critical_daylength_h} h` : ""}`);
      add("积温基点", typeof traits.gdd_base_c === "number" ? `${traits.gdd_base_c} °C` : "");
      add("耐寒", typeof traits.frost_tolerance_c === "number" ? `${traits.frost_tolerance_c} °C` : "");
      add("热害", typeof traits.heat_stress_c === "number" ? `${traits.heat_stress_c} °C` : "");
      add("水分策略", traitLabel(traits.irrigation_strategy, { pulse: "少量多次", deep: "深灌" }));
      add("最大干燥", typeof traits.max_dry_down_pct === "number" ? `${traits.max_dry_down_pct}%` : "");
      add("耐旱", traitLabel(traits.drought_sensitivity, SENSITIVITY_LABELS));
      add("耐涝", traitLabel(traits.waterlogging_sensitivity, SENSITIVITY_LABELS));
      add("病害", traits.disease_risks);
      add("虫害", traits.pest_risks);
      add("土壤参考", traits.soil_ph_range ? `pH ${rangeText(traits.soil_ph_range)} · EC ${rangeText(traits.soil_ec_range) || "—"} · CO₂ ${rangeText(traits.co2_range) || "—"}` : "");
      add("采收", traits.harvest_window);
      add("来源", traits.source);
      add("置信度", traitLabel(traits.confidence, SENSITIVITY_LABELS));
    }

    if (note) {
      note.textContent = "";
      const notes = [];
      if (Array.isArray(stageInfo.advice)) notes.push(...stageInfo.advice);
      if (typeof stageInfo.days_to_next_stage === "number") {
        notes.push(`距下一阶段约 ${stageInfo.days_to_next_stage} 天（档案参考）。`);
      }
      if (typeof stageInfo.gdd_to_next_stage === "number") {
        notes.push(`距下一阶段积温约 ${stageInfo.gdd_to_next_stage} °C·d（档案参考）。`);
      }
      const ranges = suit.ranges || {};
      if (Array.isArray(ranges.air_temp_day) || Array.isArray(ranges.air_temp_night)) {
        notes.push(`日温 ${rangeText(ranges.air_temp_day, " °C") || "未提供"} / 夜温 ${rangeText(ranges.air_temp_night, " °C") || "未提供"}。`);
      }
      if (Array.isArray(ranges.vpd_kpa)) {
        notes.push(`VPD 目标 ${rangeText(ranges.vpd_kpa, " kPa")}（档案参考，不参与评分）。`);
      }
      if (Array.isArray(ranges.dli_mol_m2_day)) {
        notes.push(`DLI 目标 ${rangeText(ranges.dli_mol_m2_day, " mol/m²·d")}（档案参考，不参与评分）。`);
      }
      note.textContent = notes.length ? notes.join(" ") : "当前阶段没有额外档案提示。";
    }
  }

  function setStatCards(containerSelector, entries) {
    const cards = $$(`${containerSelector} .grid.stats .stat`);
    entries.forEach((entry, index) => {
      const card = cards[index];
      if (!card) return;
      const valueNode = card.querySelector(".stat-value");
      if (valueNode) {
        valueNode.textContent = entry.value && entry.value.valid
          ? (entry.digits ? num(entry.value.value, entry.digits) : num(entry.value.value))
          : "—";
        if (entry.value && entry.value.valid) {
          const unit = make("span", "unit", entry.unit);
          valueNode.appendChild(unit);
        }
      }
      const foot = card.querySelector(".stat-foot");
      if (foot) {
        foot.textContent = "";
        const status = statusOf(entry.value);
        const badge = make("span", status === "在线" ? "up" : "", status);
        badge.style.color = statusColor(status);
        foot.appendChild(badge);
        foot.appendChild(document.createTextNode(` · ${entry.label}`));
      }
    });
  }

  function renderSensorList() {
    const rows = $$(".sensor-list .sensor");
    const soil = reading("soil");
    const temp = reading("air_temp");
    const humidity = reading("air_humidity");
    const light = reading("light");
    const entries = [
      { value: soil, text: soil && soil.valid ? `${num(soil.value)}%` : "—", bus: "ADC", status: statusOf(soil) },
      {
        value: temp,
        text: temp && temp.valid ? `${num(temp.value, 1)}° / ${humidity && humidity.valid ? num(humidity.value) : "—"}%` : "—",
        bus: "I²C",
        status: statusOf(temp && temp.valid ? temp : humidity)
      },
      { value: light, text: light && light.valid ? num(light.value) : "—", bus: "I²C", status: statusOf(light) }
    ];
    entries.forEach((entry, index) => {
      const row = rows[index];
      if (!row) return;
      const value = row.querySelector(".sensor-value");
      const note = row.querySelector(".sensor-note");
      if (value) value.textContent = entry.text;
      if (note) {
        note.textContent = `● ${entry.status} · ${entry.bus}`;
        note.style.color = statusColor(entry.status);
      }
    });
  }

  function renderEnvironment() {
    if (!state.data) return;
    const soil = reading("soil");
    const temp = reading("air_temp");
    const humidity = reading("air_humidity");
    const light = reading("light");
    setStatCards("#environment", [
      { value: soil, unit: "%", digits: 0, label: "HW-390 · ADC" },
      { value: temp, unit: "°C", digits: 1, label: "SHT31" },
      { value: humidity, unit: "%", digits: 0, label: "SHT31" },
      { value: light, unit: "lx", digits: 0, label: "BH1750" }
    ]);

    const card = $("#environment > article.card");
    if (!card) return;
    card.textContent = "";
    card.appendChild(make("div", "card-title", "传感器状态与数据说明"));
    const table = make("div", "agri-table");
    const header = make("div", "agri-table-row agri-table-head");
    ["监测项", "当前值", "状态", "接口"].forEach((label) => header.appendChild(make("span", "", label)));
    table.appendChild(header);
    const rows = [
      ["土壤湿度", soil && soil.valid ? `${num(soil.value)}%` : "—", statusOf(soil), "ADC"],
      ["空气温度", temp && temp.valid ? `${num(temp.value, 1)}°C` : "—", statusOf(temp), "I²C"],
      ["空气湿度", humidity && humidity.valid ? `${num(humidity.value)}%` : "—", statusOf(humidity), "I²C"],
      ["光照强度", light && light.valid ? `${num(light.value)} lx` : "—", statusOf(light), "I²C"]
    ];
    rows.forEach((row) => {
      const line = make("div", "agri-table-row");
      line.appendChild(make("span", "", row[0]));
      line.appendChild(make("span", "", row[1]));
      const status = make("span", "", row[2]);
      status.style.color = statusColor(row[2]);
      line.appendChild(status);
      line.appendChild(make("span", "agri-muted", row[3]));
      table.appendChild(line);
    });
    card.appendChild(table);
    card.appendChild(
      make(
        "p",
        "agri-muted",
        "土壤湿度必须完成干燥/湿润两点校准；未校准或数据过期时显示“未标定/数据过期”，自动灌溉不会启动。所有数值均来自设备端 /api/v1/state。"
      )
    );
  }

  function renderIrrigation() {
    if (!state.data) return;
    renderPump();
  }

  function renderPump() {
    const irr = (state.data && state.data.irrigation) || {};
    const pump = Boolean(irr.pump);
    const fault = irr.state === "fault";
    const states = [$("#pumpState"), $("#pumpState2")];
    states.forEach((node) => {
      if (!node) return;
      node.classList.toggle("running", pump);
      const label = node.querySelector("span");
      if (label) label.textContent = fault ? "水泵故障" : pump ? "水泵运行中" : "水泵已停止";
    });
    [$("#pumpSwitch"), $("#pumpSwitch2")].forEach((button) => {
      if (!button) return;
      button.classList.toggle("on", pump);
      button.setAttribute("aria-pressed", String(pump));
      button.setAttribute("aria-label", "水泵开关");
    });
    const mode = $("#modeSelect");
    if (mode && irr.mode) mode.value = irr.mode;
    const pumpMode = $("#pumpMode");
    if (pumpMode) pumpMode.textContent = irr.mode === "manual" ? "手动模式" : "自动模式";

    const metaBoxes = $$(".pump-meta .meta-box");
    if (metaBoxes[1]) {
      const small = metaBoxes[1].querySelector("small");
      const strong = metaBoxes[1].querySelector("strong");
      if (small) small.textContent = "近 24 小时";
      const now = (state.data.device && state.data.device.now) || Math.floor(Date.now() / 1000);
      const count = (irr.history || []).filter((record) => (record.start_ts || 0) >= now - 86400).length;
      if (strong) strong.textContent = `${count} 次`;
    }

    const threshold = $("#irrigation .irrigation-card:nth-child(2) input.select");
    const maxRun = $$("#irrigation .irrigation-card:nth-child(2) input.select")[1];
    if (threshold) threshold.value = `${num(irr.threshold)}%`;
    if (maxRun) maxRun.value = `${num(irr.max_run_s)} 秒`;

    renderIrrigationHistory(irr);
  }

  function renderIrrigationHistory(irr) {
    let box = $("#irrigationHistory");
    if (!box) {
      const card = $("#irrigation .irrigation-card");
      if (!card) return;
      box = make("div", "agri-history");
      box.id = "irrigationHistory";
      card.appendChild(box);
    }
    box.textContent = "";
    box.appendChild(make("div", "card-sub", "最近灌溉记录"));
    const records = (irr.history || []).slice(0, 5);
    if (!records.length) {
      box.appendChild(make("div", "agri-muted", "暂无灌溉记录"));
      return;
    }
    records.forEach((record) => {
      const trigger = record.trigger === "auto" ? "自动" : "手动";
      const duration = record.duration_s === null || record.duration_s === undefined ? "进行中" : `${record.duration_s}s`;
      box.appendChild(make("div", "agri-history-row", `${shortTime(record.start_ts)} · ${trigger} · ${duration}`));
    });
  }

  function renderChart() {
    const wrap = $(".chart-card .chart-wrap");
    if (!wrap) return;
    const points = (state.history || []).filter(
      (point) => point && typeof point.temp === "number"
    );
    const liveTemp = reading("air_temp");
    const liveHumidity = reading("air_humidity");
    const liveSoil = reading("soil");
    const liveLight = reading("light");
    const liveTs = state.data && state.data.meta ? Number(state.data.meta.ts) : 0;
    if (liveTs && points.length && liveTemp && liveTemp.valid) {
      const lastTs = Number(points[points.length - 1].ts || 0);
      if (liveTs > lastTs + 30) {
        points.push({
          ts: liveTs,
          temp: liveTemp.value,
          humidity: liveHumidity && liveHumidity.valid ? liveHumidity.value : null,
          soil: liveSoil && liveSoil.valid ? liveSoil.value : null,
          light: liveLight && liveLight.valid ? liveLight.value : null
        });
      }
    }
    const soilPoints = points.filter((point) => typeof point.soil === "number");
    const humidityPoints = points.filter((point) => typeof point.humidity === "number");
    const lightPoints = points.filter((point) => typeof point.light === "number");
    const hasSoil = soilPoints.length >= 2;
    const hasHumidity = humidityPoints.length >= 2;
    const hasLight = lightPoints.length >= 2;
    const calibration = state.data && state.data.config ? state.data.config.calibration || {} : {};
    const calibrated = calibration.soil_dry !== null && calibration.soil_dry !== undefined
      && calibration.soil_wet !== null && calibration.soil_wet !== undefined;
    const soilLegend = hasSoil
      ? "土壤湿度（右轴 %）"
      : calibrated ? "土壤湿度（等待采样）" : "土壤湿度未标定";
    const humidityLegend = hasHumidity ? "空气湿度（右轴 %）" : "空气湿度（等待采样）";
    const lightLegend = hasLight ? "光照（内右轴 lx）" : "光照（等待采样）";
    const legend = $(".chart-card .legend");
    if (legend) {
      legend.innerHTML = [
        `<span><i style="background:#438967"></i>空气温度（左轴 °C）</span>`,
        `<span><i style="background:#4e8fb5"></i>${humidityLegend}</span>`,
        `<span><i style="background:#d1a45a"></i>${soilLegend}</span>`,
        `<span><i style="background:#c9a227"></i>${lightLegend}</span>`
      ].join("");
    }
    if (points.length < 2) {
      wrap.textContent = "";
      wrap.appendChild(make("div", "empty", points.length ? "历史点不足，等待下一采样" : "暂无历史数据"));
      return;
    }
    const width = 650;
    const height = 210;
    const left = 40;
    const right = 72;
    const top = 25;
    const bottom = 45;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const temps = points.map((point) => Number(point.temp));
    let minTemp = Math.min.apply(null, temps);
    let maxTemp = Math.max.apply(null, temps);
    if (maxTemp - minTemp < 1) {
      minTemp -= 1;
      maxTemp += 1;
    }
    const pad = (maxTemp - minTemp) * 0.15;
    minTemp -= pad;
    maxTemp += pad;

    const lightValues = lightPoints.map((point) => Number(point.light));
    const maxLight = Math.max(1, Math.max.apply(null, lightValues.length ? lightValues : [1]) * 1.15);

    const x = (index) => left + (plotWidth * index) / (points.length - 1);
    const yTemp = (value) => top + plotHeight - ((value - minTemp) / (maxTemp - minTemp)) * plotHeight;
    const yPercent = (value) => top + plotHeight - (Math.max(0, Math.min(100, value)) / 100) * plotHeight;
    const yLight = (value) => top + plotHeight - (Math.max(0, Math.min(maxLight, value)) / maxLight) * plotHeight;

    const tempPath = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)} ${yTemp(Number(point.temp)).toFixed(1)}`).join(" ");
    let humidityPath = "";
    let humidityStarted = false;
    points.forEach((point, index) => {
      if (typeof point.humidity === "number") {
        humidityPath += `${humidityStarted ? "L" : "M"}${x(index).toFixed(1)} ${yPercent(Number(point.humidity)).toFixed(1)} `;
        humidityStarted = true;
      } else {
        humidityStarted = false;
      }
    });
    let lightPath = "";
    let lightStarted = false;
    points.forEach((point, index) => {
      if (typeof point.light === "number") {
        lightPath += `${lightStarted ? "L" : "M"}${x(index).toFixed(1)} ${yLight(Number(point.light)).toFixed(1)} `;
        lightStarted = true;
      } else {
        lightStarted = false;
      }
    });
    let soilPath = "";
    let soilStarted = false;
    points.forEach((point, index) => {
      if (typeof point.soil === "number") {
        soilPath += `${soilStarted ? "L" : "M"}${x(index).toFixed(1)} ${yPercent(Number(point.soil)).toFixed(1)} `;
        soilStarted = true;
      } else {
        soilStarted = false;
      }
    });
    const areaPath = `${tempPath} L${x(points.length - 1).toFixed(1)} ${(top + plotHeight).toFixed(1)} L${left} ${(top + plotHeight).toFixed(1)} Z`;

    const grid = [0, 1 / 3, 2 / 3, 1].map((ratio) => top + plotHeight * ratio);
    const plotRight = width - right;
    const gridMarkup = grid.map((y) => `<path d="M${left} ${y.toFixed(1)}H${plotRight}" stroke="#edf1ed" stroke-width="1"/>`).join("");
    const tempLabels = [0, 0.5, 1].map((ratio) => {
      const value = maxTemp - (maxTemp - minTemp) * ratio;
      const y = top + plotHeight * ratio;
      return `<text x="5" y="${(y + 4).toFixed(1)}" fill="#9aa89f" font-size="10">${value.toFixed(1)}°</text>`;
    }).join("");
    const percentLabels = [0, 0.5, 1].map((ratio) => {
      const value = 100 - 100 * ratio;
      const y = top + plotHeight * ratio;
      return `<text x="${width - 8}" y="${(y + 4).toFixed(1)}" text-anchor="end" fill="#b39a6d" font-size="9">${value}%</text>`;
    }).join("");
    const lightLabels = [0, 0.5, 1].map((ratio) => {
      const value = maxLight - maxLight * ratio;
      const y = top + plotHeight * ratio;
      const text = value >= 100 ? String(Math.round(value)) : value.toFixed(1);
      return `<text x="${width - 60}" y="${(y + 4).toFixed(1)}" fill="#c9a227" font-size="9">${text}</text>`;
    }).join("");
    const soilAxisNote = hasSoil
      ? ""
      : `<text x="${width - 8}" y="${(top + plotHeight / 2).toFixed(1)}" text-anchor="end" fill="#b39a6d" font-size="9">${calibrated ? "等待采样" : "未标定"}</text>`;
    const lightAxisCaption = `<text x="${width - 60}" y="12" fill="#c9a227" font-size="9">lx</text>`;
    const percentAxisCaption = `<text x="${width - 8}" y="12" text-anchor="end" fill="#b39a6d" font-size="9">%</text>`;
    const xLabels = [0, 1, 2, 3].map((index) => {
      const pointIndex = Math.min(points.length - 1, Math.round(((points.length - 1) * index) / 3));
      const label = new Date(Number(points[pointIndex].ts) * 1000).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
      return `<text x="${x(pointIndex).toFixed(1)}" y="${height - 20}" text-anchor="middle" fill="#9aa89f" font-size="10">${label}</text>`;
    }).join("");

    const svg = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="空气温度、空气湿度、土壤湿度与光照历史曲线">
      <defs><linearGradient id="agriArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#5c9b78" stop-opacity=".2"/><stop offset="1" stop-color="#5c9b78" stop-opacity="0"/></linearGradient></defs>
      ${gridMarkup}${tempLabels}${percentLabels}${lightLabels}${lightAxisCaption}${percentAxisCaption}${soilAxisNote}${xLabels}
      <path d="${areaPath}" fill="url(#agriArea)"/>
      ${hasLight ? `<path d="${lightPath}" fill="none" stroke="#c9a227" stroke-width="1.8" stroke-linecap="round" stroke-dasharray="2 3"/>` : ""}
      ${hasSoil ? `<path d="${soilPath}" fill="none" stroke="#d1a45a" stroke-width="2.3" stroke-linecap="round" stroke-dasharray="5 4"/>` : ""}
      ${hasHumidity ? `<path d="${humidityPath}" fill="none" stroke="#4e8fb5" stroke-width="2" stroke-linecap="round"/>` : ""}
      <path d="${tempPath}" fill="none" stroke="#438967" stroke-width="2.7" stroke-linecap="round"/>
    </svg>`;
    wrap.innerHTML = svg;
  }

  function reasonText(reason) {
    if (!reason) return "数据不足";
    const parts = String(reason).split(":");
    const key = parts[0];
    const labels = { soil: "土壤湿度", temp: "空气温度", humidity: "空气湿度", light: "光照" };
    const label = labels[key] || key;
    const detail = parts.slice(1).join(":").trim();
    if (detail === "uncalibrated") return `${label}未标定（需干湿两点校准）`;
    if (detail === "stale") return `${label}数据过期`;
    if (detail === "missing") return `${label}无数据`;
    return detail ? `${label}：${detail}` : `${label}数据不可用`;
  }

  function renderScore() {
    const suit = (state.data && state.data.suitability) || {};
    const score = suit.score;
    const number = $(".score-number");
    const status = $(".score-status");
    const circle = $(".score-ring circle:nth-child(2)");
    const topNote = $(".score-top span:last-child");
    const sub = $(".score-card .card-sub");
    if (sub && suit.profile_name) {
      sub.textContent = `${suit.profile_name} · ${suit.stage_name || ""} · 当前环境评估`;
    }
    if (topNote) topNote.textContent = score === null || score === undefined ? "数据不足" : "实时计算";

    if (score === null || score === undefined) {
      if (number) number.textContent = "—";
      if (status) {
        const reasons = (suit.reasons || []).map(reasonText);
        status.textContent = reasons[0] || "等待有效数据";
      }
      if (circle) circle.setAttribute("stroke-dashoffset", "371");
      $$(".score-detail .score-row").forEach((row) => {
        const bar = row.querySelector(".bar b");
        const strong = row.querySelector("strong");
        if (bar) bar.style.width = "0%";
        if (strong) strong.textContent = "—";
      });
      return;
    }

    if (number) number.textContent = String(score);
    if (status) {
      status.textContent = score >= 80 ? "环境状态良好" : score >= 60 ? "基本适宜" : score >= 40 ? "需要关注" : "环境异常";
      status.style.color = score >= 80 ? "var(--green2)" : score >= 60 ? "var(--gold)" : "var(--red)";
    }
    if (circle) {
      const offset = 371 * (1 - score / 100);
      circle.setAttribute("stroke-dashoffset", offset.toFixed(1));
      circle.setAttribute("stroke", score >= 80 ? "#4d956f" : score >= 60 ? "#c69a48" : "#c65c4e");
    }
    const components = suit.components || {};
    const order = ["temp", "humidity", "soil", "light"];
    $$(".score-detail .score-row").forEach((row, index) => {
      const value = components[order[index]];
      const bar = row.querySelector(".bar b");
      const strong = row.querySelector("strong");
      if (bar) bar.style.width = `${value === undefined ? 0 : value}%`;
      if (strong) strong.textContent = value === undefined ? "—" : String(value);
    });
  }

  // ---------------------------------------------------------------- calendar
  function populateSeasonSelect() {
    const select = $("#seasonSelect");
    if (!select || !state.terms || !state.terms.length) return;
    if (select.options.length === state.terms.length) return;
    select.textContent = "";
    state.terms.forEach((term) => {
      const option = document.createElement("option");
      option.value = term.name;
      option.textContent = term.name;
      select.appendChild(option);
    });
  }

  function renderCalendar() {
    const device = state.data ? state.data.device : null;
    if (device && device.time_synced === false && !state.termTouched) {
      renderTimeNotSynced();
      return;
    }
    const current = state.data && state.data.solar_term ? state.data.solar_term : null;
    if (!state.terms || !state.terms.length) {
      if (!current) return;
      if (!state.termTouched) state.selectedTerm = current.name;
      renderTerm(state.selectedTerm || current.name);
      return;
    }
    const currentName = current ? current.name : state.terms[0].name;
    if (!state.termTouched) state.selectedTerm = currentName;
    if (!state.selectedTerm) state.selectedTerm = currentName;
    populateSeasonSelect();
    renderTerm(state.selectedTerm);
  }

  function renderTimeNotSynced() {
    const kicker = $(".season-kicker");
    if (kicker) kicker.textContent = "二十四节气";
    const hero = $("#seasonHero");
    if (hero) hero.dataset.season = "";
    const name = $("#seasonName");
    if (name) name.textContent = "—";
    const intro = $("#seasonIntro");
    if (intro) intro.textContent = "设备时间尚未同步，无法计算当前节气。打开设置页或等待浏览器校时后再试。";
    const date = $("#seasonDate");
    if (date) date.textContent = "—";
    const season = $("#seasonSeason");
    if (season) season.textContent = "—";
    const angle = $(".season-meta span:last-child b");
    if (angle) angle.textContent = "—";
    ["proverbOne", "proverbTwo", "proverbThree"].forEach((id) => {
      const node = document.getElementById(id);
      if (node) node.textContent = "—";
    });
    ["proverbNoteOne", "proverbNoteTwo", "proverbNoteThree"].forEach((id) => {
      const node = document.getElementById(id);
      if (node) node.textContent = "设备时间未同步";
    });
    const customList = $("#customList");
    if (customList) {
      customList.textContent = "";
      customList.appendChild(make("div", "info-item", "设备时间未同步，无法自动识别当前节气。"));
    }
    const tips = $("#farmingTips");
    if (tips) {
      tips.textContent = "";
      tips.appendChild(make("div", "farming-tip", "设备时间未同步，暂不展示当前节气农事建议。"));
    }
    const select = $("#seasonSelect");
    if (select) select.value = "";
    $$(".term-chip").forEach((chip) => chip.classList.remove("active"));
  }

  function termByName(name) {
    if (state.terms) {
      const found = state.terms.find((term) => term.name === name);
      if (found) return found;
    }
    if (state.data && state.data.solar_term && state.data.solar_term.name === name) return state.data.solar_term;
    return null;
  }

  function renderTerm(name) {
    const term = termByName(name);
    if (!term) {
      notify("该节气的内容尚未载入");
      return;
    }
    const kicker = $(".season-kicker");
    if (kicker) kicker.textContent = `二十四节气 · ${term.season || ""}`;
    const hero = $("#seasonHero");
    if (hero) hero.dataset.season = term.name;
    const nameNode = $("#seasonName");
    if (nameNode) nameNode.textContent = term.name;
    const intro = $("#seasonIntro");
    if (intro) intro.textContent = term.intro || "暂无简介。";
    const date = $("#seasonDate");
    if (date) date.textContent = term.date_hint ? `通常在 ${term.date_hint} 前后` : "日期参考暂缺";
    const season = $("#seasonSeason");
    if (season) {
      const order = Number.isFinite(Number(term.index)) && Number(term.index) >= 0 ? (Number(term.index) % 6) + 1 : "—";
      season.textContent = `${term.season || ""} · 第 ${order} 个节气`;
    }
    const angle = $(".season-meta span:last-child b");
    if (angle) angle.textContent = `太阳黄经约 ${term.angle}°`;

    const sayings = term.proverbs || [];
    for (let index = 0; index < 3; index += 1) {
      const strong = document.getElementById(["proverbOne", "proverbTwo", "proverbThree"][index]);
      const note = document.getElementById(["proverbNoteOne", "proverbNoteTwo", "proverbNoteThree"][index]);
      const item = sayings[index];
      if (strong) strong.textContent = item ? item[0] : "暂无收录";
      if (note) note.textContent = item ? item[1] : "该节气的详细文化内容将在后续版本补充。";
    }

    const customList = $("#customList");
    if (customList) {
      customList.textContent = "";
      const customs = term.customs || [];
      if (!customs.length) {
        customList.appendChild(make("div", "info-item", "暂无收录，后续版本补充。"));
      } else {
        customs.forEach((item, index) => {
          const row = make("div", "info-item");
          const icon = make("div", "info-icon", `0${index + 1}`);
          const body = make("div");
          body.appendChild(make("strong", "", item[0]));
          body.appendChild(make("p", "", item[1]));
          row.appendChild(icon);
          row.appendChild(body);
          customList.appendChild(row);
        });
      }
    }

    const tips = $("#farmingTips");
    if (tips) {
      tips.textContent = "";
      const items = term.tips || [];
      if (!items.length) {
        tips.appendChild(make("div", "farming-tip", "暂无收录，后续版本补充。"));
      } else {
        items.forEach((item) => {
          const box = make("div", "farming-tip");
          box.appendChild(make("b", "", item[0]));
          box.appendChild(make("p", "", item[1]));
          tips.appendChild(box);
        });
      }
    }

    const select = $("#seasonSelect");
    if (select) select.value = term.name;
    $$(".term-chip").forEach((chip) => {
      const label = chip.childNodes[0] ? chip.childNodes[0].textContent.trim() : "";
      chip.classList.toggle("active", label === term.name);
    });
    renderPlantProfile();
  }

  // ------------------------------------------------------------------ device
  function soilRaw() {
    const soil = state.data && state.data.sensors ? state.data.sensors.soil : null;
    return soil && typeof soil.raw === "number" ? soil.raw : null;
  }

  function renderCalibration() {
    const card = $("#calibrationCard");
    if (!card) return;
    const config = (state.data && state.data.config) || {};
    const cal = config.calibration || {};
    const dry = $("#soilDry");
    const wet = $("#soilWet");
    const dryValue = cal.soil_dry === null || cal.soil_dry === undefined ? "" : String(cal.soil_dry);
    const wetValue = cal.soil_wet === null || cal.soil_wet === undefined ? "" : String(cal.soil_wet);
    if (!state.calibrationDraft) {
      if (dry && document.activeElement !== dry) dry.value = dryValue;
      if (wet && document.activeElement !== wet) wet.value = wetValue;
    }
    const raw = soilRaw();
    const hint = $("#calibrationHint");
    if (hint) hint.textContent = raw === null ? "当前 ADC：—" : `当前 ADC：${raw}`;
    const badge = $("#calibrationBadge");
    const calibrated = cal.soil_dry !== null && cal.soil_dry !== undefined && cal.soil_wet !== null && cal.soil_wet !== undefined;
    if (badge) {
      badge.textContent = calibrated ? "已标定" : "未标定";
      badge.classList.toggle("ok", calibrated);
    }
  }

  function captureCalibration(input) {
    const raw = soilRaw();
    if (raw === null) {
      notify("设备暂未返回 ADC 原始值，等下一轮采样后再试");
      return;
    }
    if (input) input.value = String(raw);
    syncCalibrationDraft();
    notify(`已填入当前 ADC：${raw}`);
  }

  function syncCalibrationDraft() {
    const dry = $("#soilDry");
    const wet = $("#soilWet");
    state.calibrationDraft = {
      dry: dry ? dry.value : "",
      wet: wet ? wet.value : ""
    };
  }

  async function saveCalibration() {
    const dry = Number($("#soilDry").value);
    const wet = Number($("#soilWet").value);
    if (!Number.isInteger(dry) || !Number.isInteger(wet) || dry < 0 || dry > 65535 || wet < 0 || wet > 65535) {
      notify("请输入 0–65535 的 ADC 原始值");
      return;
    }
    if (Math.abs(dry - wet) < 500) {
      notify("干端与湿端差值至少 500，请重新取样");
      return;
    }
    const button = $("#saveCalibration");
    if (button) button.disabled = true;
    try {
      const config = await api("/config", {
        method: "PUT",
        body: { calibration: { soil_dry: dry, soil_wet: wet } }
      });
      if (state.data) state.data.config = config;
      state.calibrationDraft = null;
      renderCalibration();
      notify("标定已保存，下一轮采样生效");
      setTimeout(fetchState, 1200);
    } catch (error) {
      notify(error.message || "标定保存失败");
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function clearCalibration() {
    if (!window.confirm("清除土壤干湿标定？清除后土壤显示未标定，自动灌溉不会启动。")) return;
    const button = $("#clearCalibration");
    if (button) button.disabled = true;
    try {
      const config = await api("/config", {
        method: "PUT",
        body: { calibration: { soil_dry: null, soil_wet: null } }
      });
      if (state.data) state.data.config = config;
      state.calibrationDraft = null;
      renderCalibration();
      notify("标定已清除");
      setTimeout(fetchState, 1200);
    } catch (error) {
      notify(error.message || "清除标定失败");
    } finally {
      if (button) button.disabled = false;
    }
  }

  function renderDevice() {
    if (!state.data) {
      renderCalibration();
      return;
    }
    const card = $("#device .card");
    if (!card) return;
    card.textContent = "";
    card.appendChild(make("div", "card-title", "设备信息"));
    const grid = make("div", "agri-grid");
    const data = state.data;
    const network = data.network || {};
    const source = data.meta && data.meta.source === "simulator" ? "开发模拟器" : "ESP32-S3 设备";
    grid.appendChild(field("主控型号", data.device.model || "ESP32-S3 N16R8"));
    grid.appendChild(field("固件平台", data.device.firmware || "MicroPython"));
    grid.appendChild(field("固件版本", data.device.version || "—"));
    grid.appendChild(field("触摸屏", "TJC3224T128_011R_A01 · 2.8 英寸"));
    grid.appendChild(field("传感器", "土壤湿度 / SHT31 / BH1750"));
    grid.appendChild(field("Wi-Fi 状态", network.status === "connected" ? "已连接" : (network.status || "未知")));
    grid.appendChild(field("局域网 IP", network.ip || "—"));
    grid.appendChild(field("运行时间", uptimeText(data.device.uptime_s)));
    grid.appendChild(field("时间同步", data.device.time_synced ? "已同步" : "未同步"));
    grid.appendChild(field("通信状态", state.online ? "在线" : "离线"));
    grid.appendChild(field("数据来源", source));
    grid.appendChild(field("最近更新", timeText(data.meta && data.meta.ts)));
    card.appendChild(grid);
    renderCalibration();
  }

  // ---------------------------------------------------------------- settings
  function renderSettings(force) {
    if (!state.data || !state.data.config) return;
    const card = $("#settings .card");
    if (!card) return;
    const config = state.data.config;
    const key = JSON.stringify({ irrigation: config.irrigation, plant: config.plant, security: state.data.security });
    if (!force && key === state.settingsKey) return;
    if (!force && card.contains(document.activeElement) && document.activeElement !== document.body) return;

    const irr = config.irrigation || {};
    const plant = config.plant || {};
    const network = state.data.network || {};
    card.textContent = "";
    card.appendChild(make("div", "card-title", "网络、系统与参数配置"));

    const info = make("div", "agri-grid");
    info.appendChild(field("当前 Wi-Fi", network.ssid || "—"));
    info.appendChild(field("连接状态", network.status === "connected" ? "已连接" : (network.status || "未知")));
    info.appendChild(field("局域网 IP", network.ip || "—"));
    info.appendChild(field("固件版本", state.data.device.version || "—"));
    info.appendChild(field("运行时间", uptimeText(state.data.device.uptime_s)));
    info.appendChild(field("设备时间", state.data.device.time_synced ? timeText(state.data.device.now) : "未同步"));
    info.appendChild(field("设备 PIN", state.data.security && state.data.security.pin_required ? "已启用" : "未启用（M1 默认关闭）"));
    card.appendChild(info);

    const form = make("form", "agri-form");
    form.appendChild(make("h3", "", "灌溉参数"));
    const mode = make("select", "agri-input");
    [["auto", "自动模式"], ["manual", "手动模式"]].forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      mode.appendChild(option);
    });
    mode.value = irr.mode || "auto";
    form.appendChild(labeled("工作模式", mode));

    const threshold = make("input", "agri-input");
    threshold.type = "number";
    threshold.min = "0";
    threshold.max = "100";
    threshold.step = "1";
    threshold.value = String(irr.soil_threshold === undefined ? 35 : irr.soil_threshold);
    form.appendChild(labeled("土壤湿度触发阈值（%）", threshold));

    const maxRun = make("input", "agri-input");
    maxRun.type = "number";
    maxRun.min = "1";
    maxRun.max = "120";
    maxRun.step = "1";
    maxRun.value = String(irr.max_run_s === undefined ? 20 : irr.max_run_s);
    form.appendChild(labeled("单次最长运行（秒）", maxRun));

    const interval = make("input", "agri-input");
    interval.type = "number";
    interval.min = "0";
    interval.max = "1440";
    interval.step = "1";
    interval.value = String(Math.round((irr.min_interval_s || 0) / 60));
    form.appendChild(labeled("自动灌溉最小间隔（分钟）", interval));

    const profile = make("select", "agri-input");
    const profileOptions = state.plantProfiles && state.plantProfiles.length
      ? state.plantProfiles
      : Object.keys(PLANT_NAMES).map((key) => ({ key, name: PLANT_NAMES[key] }));
    profileOptions.forEach((item) => {
      const option = document.createElement("option");
      option.value = item.key;
      option.textContent = item.name;
      profile.appendChild(option);
    });
    if (!profileOptions.some((item) => item.key === plant.profile)) {
      const option = document.createElement("option");
      option.value = plant.profile || "general";
      option.textContent = plant.profile || "general";
      profile.appendChild(option);
    }
    profile.value = plant.profile || "general";
    form.appendChild(labeled("植物档案", profile));

    const stage = make("select", "agri-input");
    Object.keys(PLANT_STAGE_NAMES).forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = PLANT_STAGE_NAMES[value];
      stage.appendChild(option);
    });
    stage.value = plant.stage || "growth";
    form.appendChild(labeled("生长阶段", stage));

    const weightGrid = make("div");
    weightGrid.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:12px";
    const weightInputs = {};
    const configuredWeights = plant.weights && typeof plant.weights === "object" ? plant.weights : {};
    PLANT_METRICS.forEach(([key, label]) => {
      const input = make("input", "agri-input");
      input.type = "number";
      input.min = "0";
      input.max = "1";
      input.step = "0.01";
      input.placeholder = "默认";
      if (typeof configuredWeights[key] === "number") input.value = String(configuredWeights[key]);
      weightInputs[key] = input;
      weightGrid.appendChild(labeled(`${label}权重（0–1）`, input));
    });
    form.appendChild(weightGrid);
    form.appendChild(make("p", "agri-muted", "四项权重全部留空时使用档案/阶段默认权重；填写时必须四项都填。"));

    const note = make("p", "agri-muted", "参数由设备端校验并保存；网页不会提前显示未执行的配置。");
    form.appendChild(note);

    const submit = make("button", "btn agri-primary", "保存配置");
    submit.type = "submit";
    form.appendChild(submit);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }
      submit.disabled = true;
      try {
        const customWeights = {};
        let weightCount = 0;
        PLANT_METRICS.forEach(([key]) => {
          const raw = weightInputs[key].value.trim();
          if (raw !== "") {
            customWeights[key] = Number(raw);
            weightCount += 1;
          }
        });
        if (weightCount > 0 && weightCount < 4) {
          notify("权重需要四项全部填写，或全部留空");
          return;
        }
        await api("/config", {
          method: "PUT",
          body: {
            irrigation: {
              mode: mode.value,
              soil_threshold: Number(threshold.value),
              max_run_s: Number(maxRun.value),
              min_interval_s: Math.round(Number(interval.value) * 60)
            },
            plant: {
              profile: profile.value,
              stage: stage.value,
              weights: weightCount === 4 ? customWeights : null
            }
          }
        });
        state.settingsKey = null;
        notify("配置已保存到设备");
        await fetchState();
      } catch (error) {
        notify(`保存失败：${error.message}`);
      } finally {
        submit.disabled = false;
      }
    });
    card.appendChild(form);
    state.settingsKey = key;
  }

  function labeled(labelText, control) {
    const label = make("label", "agri-labeled");
    label.appendChild(make("span", "", labelText));
    label.appendChild(control);
    return label;
  }

  // ------------------------------------------------------------------ chrome
  function updateChrome() {
    const data = state.data;
    const dateLabel = $("#dateLabel");
    if (dateLabel) {
      if (!state.online) {
        dateLabel.textContent = data && data.meta ? `最后更新 ${timeText(data.meta.ts)}` : "设备离线";
      } else if (data && data.device && data.device.time_synced && data.device.now_local) {
        dateLabel.textContent = data.device.now_local.replace("T", " ").slice(0, 16);
      } else if (data && data.device && data.device.time_synced) {
        dateLabel.textContent = timeText(data.device.now);
      } else {
        dateLabel.textContent = "时间未同步";
      }
    }
    const connection = $(".sidebar-bottom .connection");
    if (connection) {
      const source = data && data.meta && data.meta.source === "simulator" ? "开发模拟器" : "";
      connection.textContent = state.online ? `设备连接状态：在线${source ? ` · ${source}` : ""}` : "设备连接状态：离线";
      const dot = connection.querySelector(".dot");
      if (dot) dot.style.background = state.online ? (source ? "var(--gold)" : "#76c991") : "var(--red)";
    }
  }

  function setBanner(errorMessage) {
    const content = $(".content");
    if (!content) return;
    let banner = $("#agriBanner");
    if (!banner) {
      banner = make("div", "agri-banner");
      banner.id = "agriBanner";
      content.insertBefore(banner, content.firstChild);
    }
    const data = state.data;
    const simulator = data && data.meta && data.meta.source === "simulator";
    document.body.classList.toggle("agri-offline", !state.online);
    if (!state.online) {
      banner.className = "agri-banner offline";
      banner.textContent = data && data.meta
        ? `设备离线 · 数据已停止更新（最后更新 ${timeText(data.meta.ts)}）${errorMessage ? ` · ${errorMessage}` : ""}`
        : `设备离线 · 无法获取设备数据${errorMessage ? ` · ${errorMessage}` : ""}`;
      banner.style.display = "block";
    } else if (simulator) {
      banner.className = "agri-banner sim";
      banner.textContent = "开发模拟器 · 当前数值由主机模拟生成，不是真实设备数据";
      banner.style.display = "block";
    } else {
      banner.style.display = "none";
    }
  }

  // -------------------------------------------------------------------- bind
  function bind() {
    $$(".nav button[data-view]").forEach((button) => {
      button.addEventListener("click", () => navTo(button.dataset.view));
    });
    $$("[data-goto]").forEach((button) => {
      button.addEventListener("click", () => navTo(button.dataset.goto));
    });
    const menu = $("#menuBtn");
    if (menu) menu.addEventListener("click", () => $("#sidebar").classList.toggle("open"));
    const refresh = $("#refreshBtn");
    if (refresh) {
      refresh.addEventListener("click", () => {
        state.historyAt = 0;
        state.backoff = POLL_MS;
        fetchState();
        fetchHistory();
        fetchTerms(true);
        notify("正在刷新设备数据");
      });
    }
    const range = $("#chartRange");
    if (range) {
      range.textContent = "";
      [["12h", "最近 12 小时"], ["24h", "最近 24 小时"], ["7d", "最近 7 天"]].forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        range.appendChild(option);
      });
      range.value = state.historyRange;
      range.addEventListener("change", () => {
        state.historyRange = range.value;
        state.history = null;
        fetchHistory();
      });
    }
    const mode = $("#modeSelect");
    if (mode) {
      mode.textContent = "";
      [["auto", "自动模式"], ["manual", "手动模式"]].forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        mode.appendChild(option);
      });
      mode.addEventListener("change", () => {
        saveIrrigation({ mode: mode.value });
      });
    }
    [$("#pumpSwitch"), $("#pumpSwitch2")].forEach((button) => {
      if (!button) return;
      button.addEventListener("click", () => {
        if (!state.data || !state.data.irrigation) return;
        control(state.data.irrigation.pump ? "stop" : "start");
      });
    });
    const seasonSelect = $("#seasonSelect");
    if (seasonSelect) {
      seasonSelect.addEventListener("change", () => {
        state.termTouched = true;
        state.selectedTerm = seasonSelect.value;
        renderTerm(seasonSelect.value);
      });
    }
    $$(".term-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const label = chip.childNodes[0] ? chip.childNodes[0].textContent.trim() : "";
        if (!label) return;
        state.termTouched = true;
        state.selectedTerm = label;
        renderTerm(label);
      });
    });
    const captureDry = $("#captureDry");
    if (captureDry) captureDry.addEventListener("click", () => captureCalibration($("#soilDry")));
    const captureWet = $("#captureWet");
    if (captureWet) captureWet.addEventListener("click", () => captureCalibration($("#soilWet")));
    ["#soilDry", "#soilWet"].forEach((selector) => {
      const input = $(selector);
      if (input) input.addEventListener("input", syncCalibrationDraft);
    });
    const saveCal = $("#saveCalibration");
    if (saveCal) saveCal.addEventListener("click", saveCalibration);
    const clearCal = $("#clearCalibration");
    if (clearCal) clearCal.addEventListener("click", clearCalibration);

    const plantFile = $("#plantFile");
    const importPlants = $("#importPlants");
    const plantStatus = $("#plantImportStatus");
    if (importPlants) {
      importPlants.addEventListener("click", async () => {
        if (!plantFile || !plantFile.files || !plantFile.files.length) {
          if (plantStatus) plantStatus.textContent = "请先选择一个 JSON 文件。";
          return;
        }
        importPlants.disabled = true;
        if (plantStatus) plantStatus.textContent = "正在读取并导入…";
        try {
          const text = await plantFile.files[0].text();
          const payload = JSON.parse(text);
          const result = await api("/plant-profiles/import", { method: "POST", body: payload, timeout: 15000 });
          state.plantProfiles = result.profiles || [];
          if (plantStatus) {
            plantStatus.textContent = `已导入：${(result.imported || []).join("、") || "（无）"}`;
          }
          plantFile.value = "";
          notify("植物档案已导入设备");
          await fetchState();
          renderSettings(true);
        } catch (error) {
          if (plantStatus) plantStatus.textContent = `导入失败：${error.message || "文件无效"}`;
          notify("植物档案导入失败");
        } finally {
          importPlants.disabled = false;
        }
      });
    }
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        clearTimeout(state.pollTimer);
      } else {
        fetchState();
      }
    });
    window.addEventListener("hashchange", applyHash);
  }

  function applyHash() {
    const name = (location.hash || "").replace("#", "");
    if (VIEW_LABELS[name]) navTo(name);
  }

  async function saveIrrigation(patch) {
    try {
      await api("/config", { method: "PUT", body: { irrigation: patch } });
      notify("配置已保存到设备");
      state.settingsKey = null;
      await fetchState();
    } catch (error) {
      notify(`保存失败：${error.message}`);
      await fetchState();
    }
  }

  async function control(action) {
    if (!state.online) {
      notify("设备离线，无法控制水泵");
      return;
    }
    const requestId = `web-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    try {
      await api("/irrigation/commands", { method: "POST", body: { action, request_id: requestId } });
      notify(action === "start" ? "启动指令已发送" : "停止指令已发送");
      await fetchState();
    } catch (error) {
      notify(error.code === "PIN_CANCELLED" ? "已取消" : `控制失败：${error.message}`);
    }
  }

  // --------------------------------------------------------------------- init
  function clearDemoValues() {
    $$(".stat-value").forEach((node) => {
      node.textContent = "—";
    });
    $$(".sensor-value").forEach((node) => {
      node.textContent = "—";
    });
    $$(".sensor-note").forEach((node) => {
      node.textContent = "等待数据";
      node.style.color = "";
    });
    [$("#pumpState"), $("#pumpState2")].forEach((node) => {
      if (!node) return;
      node.classList.remove("running");
      const label = node.querySelector("span");
      if (label) label.textContent = "状态未知";
    });
    const pumpMode = $("#pumpMode");
    if (pumpMode) pumpMode.textContent = "—";
    const pumpMeta = $$(".pump-meta .meta-box strong");
    if (pumpMeta[1]) pumpMeta[1].textContent = "—";
    const scoreRing = $(".score-ring circle:nth-child(2)");
    if (scoreRing) scoreRing.setAttribute("stroke-dashoffset", "371");
    const scoreNumber = $(".score-number");
    if (scoreNumber) scoreNumber.textContent = "—";
    const scoreStatus = $(".score-status");
    if (scoreStatus) scoreStatus.textContent = "等待设备数据";
    $$(".score-detail .score-row").forEach((row) => {
      const bar = row.querySelector(".bar b");
      const strong = row.querySelector("strong");
      if (bar) bar.style.width = "0%";
      if (strong) strong.textContent = "—";
    });
    const chart = $(".chart-card .chart-wrap");
    if (chart) {
      chart.textContent = "";
      chart.appendChild(make("div", "empty", "等待设备数据…"));
    }
    const deviceCard = $("#device .card");
    if (deviceCard) {
      deviceCard.textContent = "";
      deviceCard.appendChild(make("div", "card-title", "设备信息"));
      deviceCard.appendChild(make("div", "empty", "等待设备数据…"));
    }
    const settingsCard = $("#settings .card");
    if (settingsCard) {
      settingsCard.textContent = "";
      settingsCard.appendChild(make("div", "card-title", "系统设置"));
      settingsCard.appendChild(make("div", "empty", "等待设备数据…"));
    }
    const seasonName = $("#seasonName");
    if (seasonName) seasonName.textContent = "加载中";
    const seasonIntro = $("#seasonIntro");
    if (seasonIntro) seasonIntro.textContent = "正在读取设备节气数据…";
    const seasonDate = $("#seasonDate");
    if (seasonDate) seasonDate.textContent = "—";
    const seasonSeason = $("#seasonSeason");
    if (seasonSeason) seasonSeason.textContent = "—";
    const seasonAngle = $(".season-meta span:last-child b");
    if (seasonAngle) seasonAngle.textContent = "—";
    ["proverbOne", "proverbTwo", "proverbThree"].forEach((id) => {
      const node = document.getElementById(id);
      if (node) node.textContent = "—";
    });
    ["proverbNoteOne", "proverbNoteTwo", "proverbNoteThree"].forEach((id) => {
      const node = document.getElementById(id);
      if (node) node.textContent = "等待设备数据";
    });
    const seasonSelect = $("#seasonSelect");
    if (seasonSelect) seasonSelect.value = "";
    const environmentCard = $("#environment > article.card");
    if (environmentCard) {
      environmentCard.textContent = "";
      environmentCard.appendChild(make("div", "card-title", "传感器状态与数据说明"));
      environmentCard.appendChild(make("div", "empty", "等待设备数据…"));
    }
  }

  function init() {
    clearDemoValues();
    bind();
    fetchTerms();
    fetchPlantProfiles();
    fetchState();
    fetchHistory();
    applyHash();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
