#include "global_parameters.hh"

// Размер пикселя детектора (10 мкм)
G4double pixelSize = 3.5 * um;

// Размер сетки (количество пикселей по одной оси)
G4int gridSize = 100;

// Ширина и толщина золотых полосок (50 мкм)
G4double slitWidth = 80. * um;

// Количество частиц на пиксель
G4int particlesPerPixel = 10;

// Тип сцинтиллятора: 0 = CsI(Tl), 1 = YAG(Tb)
G4int scintillatorType = 0;
