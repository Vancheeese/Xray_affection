#include "global_parameters.hh"

// Размер пикселя детектора (10 мкм)
G4double pixelSize = 3.5 * um;

// Размер сетки (количество пикселей по одной оси)
G4int gridSize = 100;

// Ширина и толщина золотых полосок (50 мкм)
G4double slitWidth = 135 * um;

// Количество частиц на пиксель
G4int particlesPerPixel = 10;

// Тип сцинтиллятора: 0 = CsI(Tl), 1 = YAG(Tb)
G4int scintillatorType = 1;

// Толщина сцинтиллятора (300 мкм)
G4double scintillatorThickness = 300 * um;

// Энергия рентгеновского излучения (30 кэВ)
G4double initialEnergy = 30. * keV;
