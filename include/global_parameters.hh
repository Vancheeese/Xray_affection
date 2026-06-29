#ifndef GLOBAL_PARAMETERS_HH
#define GLOBAL_PARAMETERS_HH

#include "globals.hh"
#include "G4SystemOfUnits.hh"

// Размер пикселя детектора (по умолчанию 10 мкм)
extern G4double pixelSize;

// Размер сетки (количество пикселей по одной оси, по умолчанию 100)
extern G4int gridSize;

// Ширина и толщина золотых полосок (по умолчанию 50 мкм)
extern G4double slitWidth;

// Количество частиц на один пиксель (по умолчанию 10)
extern G4int particlesPerPixel;

// Тип сцинтиллятора: 0 = CsI(Tl), 1 = YAG(Tb)
extern G4int scintillatorType;

#endif
