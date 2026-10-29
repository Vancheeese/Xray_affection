#include "global_parameters.hh"

G4double pixelSize = 3.5 * um;
G4int    gridSize  = 100;
G4double slitWidth = 6 * um;
G4int    particlesPerPixel = 1000;
G4double scintillatorThickness = 1200 * um;
G4double initialEnergy = 17.5 * keV;

// ===== Параметры источника излучения =====
// По умолчанию — реалистичный спектр Mo-анода.
// Установите false, чтобы вернуться к идеальному монохроматическому пучку.
G4bool useRealisticSpectrum = true;

// ===== Оптическая система =====
G4double lensMagnification   = 2.7;
G4double lensPlaneZ          = 15.0 * mm;        // центр линзы
G4double lensFocalLength     = 10.93 * mm;       // пересчитается в Construct()
G4double lensCurvatureRadius = 10.06 * mm;       // R = 2(n-1)f
G4double lensCenterThickness = 40.0 * um;        // под DOF ≈ 0.3 мм
G4double lensRefractiveIndex = 1.46;             // SiO2 (плавленый кварц)
G4double lensRadius          = 0.64 * mm;        // оценка апертуры ≈ sqrt(R*t)
// ===== Фокусировка по глубине сцинтиллятора =====
// По умолчанию — центр (для 1200 мкм это 600 мкм).
G4double focusDepthFromBack = 600.0 * um;