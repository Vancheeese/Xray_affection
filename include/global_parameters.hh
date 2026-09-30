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

// Энергия рентгеновского излучения (по умолчанию 8 кэВ)
extern G4double initialEnergy;

// Количество частиц на пиксель (по умолчанию 200)
extern G4int particlesPerPixel;

// Толщина сцинтиллятора (по умолчанию 30 мкм)
extern G4double scintillatorThickness;

// ===== Параметры оптической системы (объектива) =====
// Увеличение (задаётся пользователем)
extern G4double lensMagnification;  // 2.7

// Фокусное расстояние (рассчитывается в PMDetectorConstruction::Construct())
extern G4double lensFocalLength;    // мм

// Положение плоскости линзы (центр линзы) вдоль оси Z
extern G4double lensPlaneZ;         // мм

// Радиус кривизны поверхностей линзы
extern G4double lensCurvatureRadius; // мм

// Толщина линзы по центру
extern G4double lensCenterThickness; // мкм

// Показатель преломления материала линзы
extern G4double lensRefractiveIndex;

// Расчётный радиус апертуры (информационно; реальная апертура —
// из пересечения двух сферических поверхностей)
extern G4double lensRadius;         // мм

#endif