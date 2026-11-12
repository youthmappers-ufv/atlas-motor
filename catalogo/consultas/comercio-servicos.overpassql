// Prancha 15 — Comércio e serviços: lojas, bancos, postos, alimentação e hospedagem.
(
  nwr({{bbox}})[shop];
  nwr({{bbox}})[amenity~"^(bank|atm|fuel|restaurant|cafe|fast_food|bar|pub|ice_cream|car_wash|car_rental|veterinary)$"];
  nwr({{bbox}})[tourism~"^(hotel|guest_house|motel|hostel)$"];
  nwr({{bbox}})[office~"^(lawyer|accountant|insurance|estate_agent|company|notary)$"];
  nwr({{bbox}})[craft];
);
