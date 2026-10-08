#include "global_parameters.hh"

G4double pixelSize = 3.5 * um;
G4int    gridSize  = 100;
G4double slitWidth = 15 * um;
G4int    particlesPerPixel = 20;
G4double scintillatorThickness = 50 * um;
G4double initialEnergy = 8. * keV;

// ===== Оптическая система =====
G4double lensMagnification   = 2.7;
G4double lensPlaneZ          = 15.0 * mm;        // центр линзы
G4double lensFocalLength     = 10.93 * mm;       // пересчитается в Construct()
G4double lensCurvatureRadius = 10.06 * mm;       // R = 2(n-1)f
G4double lensCenterThickness = 40.0 * um;        // под DOF ≈ 0.3 мм
G4double lensRefractiveIndex = 1.46;             // SiO2 (плавленый кварц)
G4double lensRadius          = 0.64 * mm;        // оценка апертуры ≈ sqrt(R*t)