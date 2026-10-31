// Configuracao do site (Observable Framework). Publicado no GitHub Pages.
export default {
  title: "Brasil em dois turnos",
  root: "src",
  base: process.env.BASE_PATH ?? "/brasil-dois-turnos/",
  lang: "pt-BR",
  theme: ["air", "near-midnight"],
  style: "styles/tema.css",
  pages: [
    { name: "Transicao entre turnos", path: "/transicao" },
    { name: "Mapa", path: "/mapa" },
    { name: "Economia", path: "/economia" },
    { name: "Historico", path: "/historico" },
    { name: "Pergunte aos dados", path: "/chat" },
    { name: "Metodologia", path: "/metodologia" },
  ],
  head: `<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap">
<meta name="description" content="Como o eleitorado se move entre o 1o e o 2o turno no Brasil. Dados abertos, estimativas com intervalo de credibilidade.">`,
  footer:
    'Dados: TSE, IBGE, BCB. Transicoes de voto sao estimativas por inferencia ecologica. <a href="./metodologia">Metodologia</a>.',
  toc: false,
  search: true,
};
