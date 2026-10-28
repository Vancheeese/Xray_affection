#ifndef GLOBAL_PARAMETERS_HH
#define GLOBAL_PARAMETERS_HH

#include "globals.hh"
#include "G4SystemOfUnits.hh"

// Размер пикселя детектора (по умолчанию 3.5 мкм)
extern G4double pixelSize;

// Размер сетки (количество пикселей по одной оси, по умолчанию 100)
extern G4int gridSize;

// Ширина и толщина золотых полосок (по умолчанию 30 мкм)
extern G4double slitWidth;

// Энергия рентгеновского излучения для ИДЕАЛЬНОГО источника
// (используется только если useRealisticSpectrum = false)
extern G4double initialEnergy;

// Количество частиц на пиксель (по умолчанию 10)
extern G4int particlesPerPixel;

// Толщина сцинтиллятора (по умолчанию 30 мкм)
extern G4double scintillatorThickness;

// ===== Параметры источника излучения =====
// true  — реалистичный спектр Mo-анода (Brems + Kα + Kβ),
//         см. PMPrimaryGenerator::SampleMolybdenumEnergy()
// false — идеальный монохроматический источник с энергией initialEnergy
extern G4bool useRealisticSpectrum;

// ===== Параметры оптической системы (объектива) =====
extern G4double lensMagnification;   // 2.7
extern G4double lensFocalLength;     // мм
extern G4double lensPlaneZ;          // мм
extern G4double lensCurvatureRadius; // мм
extern G4double lensCenterThickness; // мкм
extern G4double lensRefractiveIndex;
extern G4double lensRadius;          // мм

extern G4double focusDepthFromBack;

#endif