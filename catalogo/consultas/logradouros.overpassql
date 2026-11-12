// Prancha 13 — Logradouros e endereços: ruas com nome e numeração predial.
(
  way({{bbox}})[highway~"^(primary|secondary|tertiary|unclassified|residential|living_street|pedestrian)(_link)?$"];
  nwr({{bbox}})["addr:housenumber"];
);
