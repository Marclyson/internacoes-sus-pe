"use strict";

const D = JSON.parse(document.getElementById("dados").textContent);
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const FAIXAS = ["75 anos ou mais", "60 a 74 anos", "45 a 59 anos", "30 a 44 anos", "15 a 29 anos", "1 a 14 anos", "Menor de 1 ano"];

// ---------------------------------------------------------------- formatação
const fmtInt = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const fmt1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const fmtReal = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });

const inteiro = (v) => fmtInt.format(v);
const pct = (v) => fmt1.format(v) + "%";
const dias = (v) => fmt1.format(v) + " dias";
const real = (v) => fmtReal.format(v);
function realCurto(v) {
  if (v >= 1e9) return "R$ " + fmt1.format(v / 1e9) + " bi";
  if (v >= 1e6) return "R$ " + fmt1.format(v / 1e6) + " mi";
  if (v >= 1e3) return "R$ " + fmtInt.format(v / 1e3) + " mil";
  return real(v);
}
function intCurto(v) {
  if (v >= 1e6) return fmt1.format(v / 1e6) + " mi";
  if (v >= 1e4) return fmt1.format(v / 1e3) + " mil";
  return inteiro(v);
}
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
// Nomes do CNES e do SIGTAP vêm em maiúsculas; deixa só a primeira letra de cada palavra.
const MINUSCULAS = new Set(["de", "da", "do", "das", "dos", "e", "em", "com", "por", "para", "a", "o", "na", "no"]);
function titulo(s) {
  if (!s) return "";
  return s.toLowerCase().split(/\s+/).map((p, i) => {
    if (i > 0 && MINUSCULAS.has(p)) return p;
    if (/^(sus|uti|imip|hc|ufpe|upe|aids|hiv|ii|iii|iv)$/.test(p)) return p.toUpperCase();
    return p.charAt(0).toUpperCase() + p.slice(1);
  }).join(" ");
}
// Procedimentos do SIGTAP: só a primeira letra maiúscula
function frase(s) {
  const t = (s || "").toLowerCase().replace(/avc/g, "AVC").replace(/uti/g, "UTI");
  return t.charAt(0).toUpperCase() + t.slice(1);
}
function romano(n) {
  const tab = [[10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"]];
  let r = "";
  for (const [v, l] of tab) while (n >= v) { r += l; n -= v; }
  return r;
}

// ---------------------------------------------------------------- dica (tooltip)
const dica = document.getElementById("dica");
function mostrarDica(alvo, x, y) {
  dica.innerHTML = alvo.dataset.dica;
  dica.hidden = false;
  const r = dica.getBoundingClientRect();
  let left = x + 14, top = y + 14;
  if (left + r.width > window.innerWidth - 8) left = x - r.width - 14;
  if (top + r.height > window.innerHeight - 8) top = y - r.height - 14;
  dica.style.left = Math.max(8, left) + "px";
  dica.style.top = Math.max(8, top) + "px";
}
document.addEventListener("mousemove", (e) => {
  const alvo = e.target.closest("[data-dica]");
  if (alvo) mostrarDica(alvo, e.clientX, e.clientY);
  else dica.hidden = true;
});
document.addEventListener("focusin", (e) => {
  const alvo = e.target.closest("[data-dica]");
  if (!alvo) return;
  const r = alvo.getBoundingClientRect();
  mostrarDica(alvo, r.left + r.width / 2, r.top);
});
document.addEventListener("focusout", () => { dica.hidden = true; });
// Conteúdo da dica, já escapado para ir dentro do atributo data-dica
const linhaDica = (rotulo, ...linhas) => esc(`<b>${esc(rotulo)}</b>` + linhas.map((l) => `<span>${esc(l)}</span>`).join(""));

// ---------------------------------------------------------------- estado
const estado = { cnes: "todos", metrica: "internacoes", todosHospitais: false };
const HOSPITAIS_VISIVEIS = 15;
const METRICAS = {
  internacoes: { rotulo: "Internações", campo: "internacoes", fmt: inteiro, curto: intCurto },
  valor: { rotulo: "Valor pago", campo: "valor", fmt: real, curto: realCurto },
  mortalidade: { rotulo: "Mortalidade", campo: "mortalidade", fmt: pct, curto: pct },
  permanencia: { rotulo: "Permanência", campo: "permanencia", fmt: dias, curto: (v) => fmt1.format(v) },
};
const hospitalPorCnes = Object.fromEntries(D.hospitais.map((h) => [h.cnes, h]));

// ---------------------------------------------------------------- blocos
function kpis(r) {
  const k = r.kpis;
  const itens = [
    ["Internações", inteiro(k.internacoes), estado.cnes === "todos" ? `em <b>${inteiro(D.total_hospitais)}</b> hospitais` : `<b>${pct((100 * k.internacoes) / D.recortes.todos.kpis.internacoes)}</b> do estado`],
    ["Valor pago pelo SUS", realCurto(k.valor_total), `<b>${real(k.valor_medio)}</b> por internação`],
    ["Permanência média", dias(k.permanencia_media), "da entrada até a alta"],
    ["Mortalidade hospitalar", pct(k.mortalidade), "internações que terminaram em óbito"],
    ["Entrada por urgência", pct(k.urgencia), "o restante foi eletivo"],
    ["Usaram UTI", pct(k.uti), "ao menos um dia de UTI"],
    ["Moram em outra cidade", pct(k.fora_municipio), "pacientes de fora do município do hospital"],
    ["Valor médio por dia", real(k.valor_total / Math.max(1, k.internacoes * k.permanencia_media)), "valor pago dividido pelos dias internados"],
  ];
  document.getElementById("kpis").innerHTML = itens.map(([rot, val, extra]) =>
    `<div class="kpi"><div class="kpi-rotulo">${rot}</div><div class="kpi-valor">${val}</div><div class="kpi-extra">${extra}</div></div>`).join("");
}

function abasMensal() {
  const el = document.getElementById("abas-mensal");
  el.innerHTML = Object.entries(METRICAS).map(([id, m]) =>
    `<button type="button" role="tab" data-metrica="${id}" aria-selected="${id === estado.metrica}">${m.rotulo}</button>`).join("");
  el.onclick = (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    estado.metrica = b.dataset.metrica;
    abasMensal();
    mensal(D.recortes[estado.cnes]);
  };
}

function mensal(r) {
  const m = METRICAS[estado.metrica];
  const porMes = Object.fromEntries(r.mensal.map((x) => [x.mes, x]));
  const max = Math.max(...r.mensal.map((x) => x[m.campo]));
  document.getElementById("mensal").innerHTML = MESES.map((nome, i) => {
    const x = porMes[i + 1];
    if (!x) return `<div class="coluna"><div class="coluna-area"></div><div class="coluna-mes">${nome}</div></div>`;
    const v = x[m.campo];
    const d = linhaDica(`${nome}/${D.ano}`,
      `${inteiro(x.internacoes)} internações`, `${real(x.valor)} pagos`, `mortalidade ${pct(x.mortalidade)}`, `permanência ${dias(x.permanencia)}`);
    return `<div class="coluna" tabindex="0" data-dica="${d}">
      <div class="coluna-area"><div class="coluna-valor">${m.curto(v)}</div><div class="coluna-barra" style="height:${(100 * v) / max * 0.85}%"></div></div>
      <div class="coluna-mes">${nome}</div></div>`;
  }).join("");
}

function barras(el, itens, total) {
  const max = Math.max(...itens.map((x) => x.n));
  el.innerHTML = `<div class="barras">${itens.map((x) => `
    <div class="barra-linha" tabindex="0" data-dica="${x.dica}">
      <div class="barra-nome" title="${esc(x.nome)}">${esc(x.nome)}</div>
      <div class="barra-trilho"><div class="barra-fill" style="width:${(100 * x.n) / max}%"></div></div>
      <div class="barra-num">${inteiro(x.n)} <small>${pct((100 * x.n) / total)}</small></div>
    </div>`).join("")}</div>`;
}

function capitulos(r) {
  const total = r.kpis.internacoes;
  barras(document.getElementById("capitulos"), r.capitulos.map((c) => {
    return {
      nome: c.nome, n: c.n,
      dica: linhaDica(c.num ? `Capítulo ${romano(c.num)} da CID-10` : c.nome, c.nome, `${inteiro(c.n)} internações (${pct((100 * c.n) / total)})`, `mortalidade ${pct(c.mortalidade)}`),
    };
  }), total);
}

function piramide(r) {
  const n = {};
  for (const x of r.piramide) n[x.faixa + "|" + x.sexo] = x.n;
  const max = Math.max(1, ...r.piramide.filter((x) => FAIXAS.includes(x.faixa)).map((x) => x.n));
  const totalM = r.piramide.filter((x) => x.sexo === "Masculino").reduce((s, x) => s + x.n, 0);
  const totalF = r.piramide.filter((x) => x.sexo === "Feminino").reduce((s, x) => s + x.n, 0);
  document.getElementById("piramide").innerHTML =
    `<div class="legenda"><span class="m">Masculino · ${pct((100 * totalM) / (totalM + totalF))}</span><span class="f">Feminino · ${pct((100 * totalF) / (totalM + totalF))}</span></div>` +
    FAIXAS.map((f) => {
      const m = n[f + "|Masculino"] || 0, fe = n[f + "|Feminino"] || 0;
      const d = linhaDica(f, `${inteiro(m)} homens`, `${inteiro(fe)} mulheres`);
      return `<div class="piramide-linha" tabindex="0" data-dica="${d}">
        <div class="piramide-lado m"><small>${intCurto(m)}</small><div class="fill" style="width:${(78 * m) / max}%"></div></div>
        <div class="piramide-faixa">${f.replace(" anos", "").replace("Menor de 1 ano", "menos de 1").replace(" ou mais", "+")}</div>
        <div class="piramide-lado f"><div class="fill" style="width:${(78 * fe) / max}%"></div><small>${intCurto(fe)}</small></div>
      </div>`;
    }).join("");
}

function procedimentos(r) {
  const max = Math.max(...r.procedimentos.map((p) => p.n));
  document.getElementById("procedimentos").innerHTML = `
    <thead><tr><th>#</th><th>Procedimento</th><th class="n">Internações</th><th></th><th class="n">Valor médio</th><th class="n">Permanência média</th></tr></thead>
    <tbody>${r.procedimentos.map((p, i) => `<tr>
      <td class="rank">${i + 1}</td>
      <td class="nome">${esc(frase(p.nome))}</td>
      <td class="n">${inteiro(p.n)}</td>
      <td class="mini"><div style="width:${(100 * p.n) / max}%"></div></td>
      <td class="n">${real(p.valor_medio)}</td>
      <td class="n">${dias(p.permanencia)}</td></tr>`).join("")}</tbody>`;
}

function leitos(r) {
  const total = r.kpis.internacoes;
  barras(document.getElementById("leitos"), r.leitos.map((l) => ({
    nome: l.nome, n: l.n, dica: linhaDica(l.nome, `${inteiro(l.n)} internações (${pct((100 * l.n) / total)})`),
  })), total);
}

function destinos() {
  const max = Math.max(...D.destinos.map((d) => d.n));
  document.getElementById("destinos").innerHTML = `<div class="barras">${D.destinos.map((d) => `
    <div class="barra-linha" tabindex="0" data-dica="${linhaDica(d.nome, `${inteiro(d.n)} internações`, `${pct(d.de_fora)} de pacientes de outras cidades`)}">
      <div class="barra-nome">${esc(d.nome)}</div>
      <div class="barra-trilho"><div class="barra-fill" style="width:${(100 * d.n) / max}%"></div></div>
      <div class="barra-num">${intCurto(d.n)} <small>${fmt1.format(d.de_fora)}% de fora</small></div>
    </div>`).join("")}</div>`;
}

function fluxo() {
  const max = Math.max(...D.fluxo.map((f) => f.n));
  document.getElementById("fluxo").innerHTML = D.fluxo.map((f) => `
    <div class="fluxo-item">
      <div class="fluxo-rota"><b>${esc(f.origem)}</b><span class="fluxo-seta" aria-label="para">→</span>${esc(f.destino)}</div>
      <div class="fluxo-n">${inteiro(f.n)}</div>
      <div class="fluxo-trilho"><div style="width:${(100 * f.n) / max}%"></div></div>
    </div>`).join("");
}

function hospitais() {
  const max = D.hospitais[0].internacoes;
  const el = document.getElementById("hospitais");
  el.innerHTML = `
    <thead><tr><th>#</th><th>Hospital</th><th class="n">Internações</th><th></th><th class="n">Valor pago</th><th class="n">Permanência</th><th class="n">Mortalidade</th><th class="n">UTI</th></tr></thead>
    <tbody>${D.hospitais.map((h, i) => `<tr tabindex="0" data-cnes="${h.cnes}" class="${h.cnes === estado.cnes ? "ativo" : ""}"${i >= HOSPITAIS_VISIVEIS && !estado.todosHospitais ? " hidden" : ""}>
      <td class="rank">${i + 1}</td>
      <td class="nome">${esc(titulo(h.nome) || "CNES " + h.cnes)}<small>${esc(h.municipio || "")}${h.esfera ? " · " + esc(titulo(h.esfera)) : ""}</small></td>
      <td class="n">${inteiro(h.internacoes)}</td>
      <td class="mini"><div style="width:${(100 * h.internacoes) / max}%"></div></td>
      <td class="n">${realCurto(h.valor_total)}</td>
      <td class="n">${dias(h.permanencia_media)}</td>
      <td class="n">${pct(h.mortalidade)}</td>
      <td class="n">${pct(h.uti)}</td></tr>`).join("")}</tbody>`;
  const escolher = (tr) => tr && selecionar(tr.dataset.cnes === estado.cnes ? "todos" : tr.dataset.cnes, true);
  el.onclick = (e) => escolher(e.target.closest("tr[data-cnes]"));
  const mais = document.getElementById("mais-hospitais");
  mais.textContent = estado.todosHospitais ? `Mostrar só os ${HOSPITAIS_VISIVEIS} primeiros` : `Mostrar os ${D.hospitais.length} hospitais`;
  mais.onclick = () => { estado.todosHospitais = !estado.todosHospitais; hospitais(); };
  el.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); escolher(e.target.closest("tr[data-cnes]")); } };
}

// ---------------------------------------------------------------- filtro
const select = document.getElementById("hospital");
select.innerHTML = `<option value="todos">Todos os hospitais (${inteiro(D.total_hospitais)})</option>` +
  D.hospitais.map((h) => `<option value="${h.cnes}">${esc(titulo(h.nome) || "CNES " + h.cnes)}</option>`).join("");
select.onchange = () => selecionar(select.value, false);

function selecionar(cnes, rolar) {
  estado.cnes = cnes;
  select.value = cnes;
  history.replaceState(null, "", cnes === "todos" ? location.pathname + location.search : "#hospital=" + cnes);
  render();
  if (rolar) document.getElementById("kpis").scrollIntoView({ behavior: "smooth", block: "start" });
}

function render() {
  const r = D.recortes[estado.cnes];
  const h = hospitalPorCnes[estado.cnes];
  document.getElementById("titulo").textContent = h ? titulo(h.nome) : `Internações do SUS em ${D.uf === "PE" ? "Pernambuco" : D.uf}`;
  document.getElementById("subtitulo").textContent = h
    ? `${h.municipio || ""} · CNES ${h.cnes} · internações de ${D.ano}`
    : `Internações hospitalares de janeiro a dezembro de ${D.ano}, pela data de competência da AIH`;
  kpis(r);
  mensal(r);
  capitulos(r);
  piramide(r);
  procedimentos(r);
  leitos(r);
  for (const tr of document.querySelectorAll("#hospitais tr[data-cnes]")) tr.classList.toggle("ativo", tr.dataset.cnes === estado.cnes);
}

document.getElementById("fonte").textContent =
  `Fonte: SIH/SUS (AIH reduzida), SIGTAP, CID-10, CNES e IBGE, todos públicos. Somente AIH do tipo normal, sem as de longa permanência. Painel gerado em ${D.gerado_em}.`;
// Link direto para um hospital: index.html#hospital=<CNES>
const doLink = /hospital=(\d{7})/.exec(location.hash);
if (doLink && D.recortes[doLink[1]]) { estado.cnes = doLink[1]; select.value = doLink[1]; }
abasMensal();
hospitais();
destinos();
fluxo();
render();
