// Prancha 14 — Bairros, distritos e povoados: a divisão interna do município.
(
  nwr({{bbox}})[place~"^(suburb|neighbourhood|quarter|village|hamlet)$"];
  relation({{bbox}})[boundary=administrative][admin_level~"^(9|10)$"];
);
