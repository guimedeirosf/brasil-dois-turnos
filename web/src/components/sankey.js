// Diagrama de fluxo 1o turno -> 2o turno a partir de fct_transicao_estimada.
import * as d3 from "npm:d3";
import { sankey, sankeyLinkHorizontal } from "npm:d3-sankey";
import { CORES, DESTINOS, ORIGENS, num, pct } from "./formatos.js";

export function diagramaTransicao(linhas, rotulos, { width = 800, height = 520 } = {}) {
  const nos = [
    ...ORIGENS.map((c) => ({ id: `o:${c}`, categoria: c, nome: `${rotulos[c]} (1o)` })),
    ...DESTINOS.map((c) => ({ id: `d:${c}`, categoria: c, nome: `${rotulos[c]} (2o)` })),
  ];
  const usados = new Set(linhas.flatMap((l) => [`o:${l.origem}`, `d:${l.destino}`]));
  const grafo = sankey()
    .nodeId((d) => d.id)
    .nodeWidth(14)
    .nodePadding(14)
    .nodeSort(null)
    .extent([
      [1, 8],
      [width - 1, height - 8],
    ])({
    nodes: nos.filter((n) => usados.has(n.id)).map((n) => ({ ...n })),
    links: linhas
      .filter((l) => l.votos_estimados > 0)
      .map((l) => ({ source: `o:${l.origem}`, target: `d:${l.destino}`, value: l.votos_estimados, ...l })),
  });

  const svg = d3
    .create("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("width", width)
    .attr("role", "img")
    .attr("aria-label", "Fluxo estimado do eleitorado entre o 1o e o 2o turno");

  svg
    .append("g")
    .attr("fill", "none")
    .selectAll("path")
    .data(grafo.links)
    .join("path")
    .attr("d", sankeyLinkHorizontal())
    .attr("stroke", (d) => CORES[d.origem])
    .attr("stroke-opacity", 0.45)
    .attr("stroke-width", (d) => Math.max(1, d.width))
    .append("title")
    .text(
      (d) =>
        `${rotulos[d.origem]} -> ${rotulos[d.destino]}\n` +
        `${pct(d.pct_estimado)} (IC 95%: ${pct(d.ic_inferior)} a ${pct(d.ic_superior)})\n` +
        `cerca de ${num(d.votos_estimados)} eleitores (estimativa)`,
    );

  const no = svg.append("g").selectAll("g").data(grafo.nodes).join("g");
  no.append("rect")
    .attr("x", (d) => d.x0)
    .attr("y", (d) => d.y0)
    .attr("height", (d) => Math.max(1, d.y1 - d.y0))
    .attr("width", (d) => d.x1 - d.x0)
    .attr("fill", (d) => CORES[d.categoria]);
  no.append("text")
    .attr("x", (d) => (d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6))
    .attr("y", (d) => (d.y1 + d.y0) / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", (d) => (d.x0 < width / 2 ? "start" : "end"))
    .attr("fill", "currentColor")
    .attr("font-size", 12)
    .text((d) => d.nome);

  return svg.node();
}
