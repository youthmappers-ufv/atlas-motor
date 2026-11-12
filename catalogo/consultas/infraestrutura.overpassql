// Prancha 17 — Infraestrutura e saneamento: energia, telecomunicações, água, esgoto e resíduos.
(
  way({{bbox}})[power~"^(line|minor_line)$"];
  nwr({{bbox}})[power~"^(substation|plant|generator|transformer)$"];
  nwr({{bbox}})[man_made~"^(water_tower|water_works|wastewater_plant|reservoir_covered|pumping_station|communications_tower|mast|tower)$"];
  nwr({{bbox}})[amenity~"^(recycling|waste_disposal|waste_transfer_station)$"];
  nwr({{bbox}})[landuse=landfill];
);
