// Prancha 10 — Hidrografia: rios, córregos, nascentes, represas e lagos.
(
  way({{bbox}})[waterway~"^(river|stream|canal|ditch|drain|dam|weir)$"];
  nwr({{bbox}})[natural~"^(water|spring|wetland)$"];
  nwr({{bbox}})[landuse~"^(reservoir|basin)$"];
);
