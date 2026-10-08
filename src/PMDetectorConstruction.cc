#include "PMDetectorConstruction.hh"
#include "G4PhysicalConstants.hh"
#include "G4Tubs.hh"
#include "G4Sphere.hh"
#include "G4SubtractionSolid.hh"
#include "G4IntersectionSolid.hh"
#include "G4Transform3D.hh"
#include "global_parameters.hh"
#include <vector>
#include <iostream>
#include "G4MultiUnion.hh"

PMDetectorConstruction::PMDetectorConstruction()
{}

PMDetectorConstruction::~PMDetectorConstruction()
{}

G4VPhysicalVolume* PMDetectorConstruction::Construct()
{
    G4double scale = 100.;
    G4bool checkOverlaps = true;

    // ===== ВАКУУМ =====
    G4double density     = universe_mean_density;
    G4double pressure    = 1.e-19 * pascal;
    G4double temperature = 0.1 * kelvin;
    new G4Material("Galactic", 1., 1.01 * g / mole, density,
                   kStateGas, temperature, pressure);

    G4NistManager* nist = G4NistManager::Instance();
    G4Material* worldMat = nist->FindOrBuildMaterial("Galactic");

    G4MaterialPropertiesTable* worldMPT = new G4MaterialPropertiesTable();
    const G4int nW = 2;
    G4double wEnergies[]  = { 1.0 * eV, 6.0 * eV };
    G4double wRindex[]    = { 1.0,    1.0    };
    G4double wAbsLength[] = { 1.0 * m, 1.0 * m };
    worldMPT->AddProperty("RINDEX",    wEnergies, wRindex,    nW);
    worldMPT->AddProperty("ABSLENGTH", wEnergies, wAbsLength, nW);
    worldMat->SetMaterialPropertiesTable(worldMPT);

    G4double xWorld = 3. / scale * m;
    G4double yWorld = 3. / scale * m;
    G4double zWorld = 1. / 3 * m;

    G4Box* solidWorld = new G4Box("solidWorld",
                                  0.5 * xWorld, 0.5 * yWorld, 0.5 * zWorld);
    G4LogicalVolume* logicWorld =
        new G4LogicalVolume(solidWorld, worldMat, "logicalWorld");
    G4VPhysicalVolume* physWorld =
        new G4PVPlacement(0, G4ThreeVector(0., 0., 0.),
                          logicWorld, "physWorld", 0, false, 0);

              // ========== ЗОЛОТАЯ СЕТКА ==========
    G4double leadSize      = pixelSize * gridSize;
    G4double slitLengthY   = leadSize;
    G4double slitThickness = slitWidth;
    G4double slitPeriod    = slitWidth + slitWidth;
    G4double barWidth      = slitWidth;
    G4double holeSize      = slitPeriod - barWidth;

    G4int    numSlits   = (G4int)(leadSize / slitPeriod);
    G4double totalWidth = numSlits * slitPeriod;
    G4double startPos   = -totalWidth / 2.0;

    G4Material* goldMat = nist->FindOrBuildMaterial("G4_Au");

    // --- сплошная золотая пластина ---
    G4Box* solidPlate = new G4Box("solidGoldPlate",
                                  0.5 * leadSize,
                                  0.5 * leadSize,
                                  0.5 * slitThickness);

    // --- все отверстия объединяем в один G4MultiUnion ---
    G4MultiUnion* holesUnion = new G4MultiUnion("holesUnion");

    G4Box* solidHole = new G4Box("solidHole",
                                 0.5 * holeSize,
                                 0.5 * holeSize,
                                 0.6 * slitThickness);  // чуть толще, чтобы пробить насквозь

    for (G4int i = 0; i < numSlits; ++i) {
        for (G4int j = 0; j < numSlits; ++j) {
            G4double x = startPos + barWidth + 0.5 * holeSize + i * slitPeriod;
            G4double y = startPos + barWidth + 0.5 * holeSize + j * slitPeriod;

            G4Transform3D tr(G4RotationMatrix(),
                             G4ThreeVector(x, y, 0.));
            holesUnion->AddNode(*solidHole, tr);
        }
    }
    holesUnion->Voxelize();   // обязательно после добавления всех узлов

    // --- одно вычитание: пластина минус объединение отверстий ---
    G4SubtractionSolid* gridSolid = new G4SubtractionSolid(
        "gridSolid", solidPlate, holesUnion);

    G4LogicalVolume* logicLead =
        new G4LogicalVolume(gridSolid, goldMat, "logicLead");

    G4VisAttributes* leadVisAtt =
        new G4VisAttributes(G4Color(1.0, 0.84, 0.0, 1.0));
    leadVisAtt->SetForceSolid(true);
    logicLead->SetVisAttributes(leadVisAtt);

    // --- ВОТ ЭТИ ДВЕ ПЕРЕМЕННЫЕ НУЖНЫ ДАЛЬШЕ ПО КОДУ ---
    G4double goldPosZ = 0.0;
    G4double offsetY  = 0.0;   // сетка центрирована, сдвига нет

    new G4PVPlacement(0, G4ThreeVector(0., offsetY, goldPosZ),
                      logicLead, "physGrid",
                      logicWorld, false, 0, checkOverlaps);

    // ========== СЦИНТИЛЛЯТОР YAG(Tb) 6% ==========
    G4double scintThickness = scintillatorThickness;
    G4double scintSizeX     = pixelSize * gridSize;
    G4double scintSizeY     = pixelSize * gridSize;

    G4Material* scintMat = new G4Material("YAG_Tb", 4.55 * g / cm3, 4);
    scintMat->AddElement(nist->FindOrBuildElement("Y"),  0.4135);
    scintMat->AddElement(nist->FindOrBuildElement("Tb"), 0.0472);
    scintMat->AddElement(nist->FindOrBuildElement("Al"), 0.2225);
    scintMat->AddElement(nist->FindOrBuildElement("O"),  0.3167);

    G4MaterialPropertiesTable* scintMPT = new G4MaterialPropertiesTable();

    const G4int nRI = 2;
    G4double riEnergies[]      = { 1.77 * eV, 4.13 * eV };
    G4double refractiveIndex[] = { 1.84, 1.84 };
    scintMPT->AddProperty("RINDEX", riEnergies, refractiveIndex, nRI);

    const G4int nAbs = 2;
    G4double absEnergies[] = { 1.77 * eV, 4.13 * eV };
    G4double absLength[]   = { 1500.0 * um, 1500.0 * um };
    scintMPT->AddProperty("ABSLENGTH", absEnergies, absLength, nAbs);

    scintMPT->AddConstProperty("SCINTILLATIONYIELD", 22000.0 / MeV);
    scintMPT->AddConstProperty("RESOLUTIONSCALE", 1.0);
    scintMPT->AddConstProperty("SCINTILLATIONTIMECONSTANT1", 65.0 * ns);
    scintMPT->AddConstProperty("SCINTILLATIONYIELD1", 0.85);
    scintMPT->AddConstProperty("SCINTILLATIONTIMECONSTANT2", 160.0 * ns);
    scintMPT->AddConstProperty("SCINTILLATIONYIELD2", 0.15);

    const G4int nScint = 9;
    G4double scintEnergies[]  = { 2.00*eV, 2.10*eV, 2.20*eV, 2.25*eV,
                                  2.30*eV, 2.35*eV, 2.50*eV, 2.70*eV, 2.90*eV };
    G4double scintIntensity[] = { 0.05, 0.20, 0.60, 0.90,
                                  1.00, 0.95, 0.40, 0.10, 0.02 };
    scintMPT->AddProperty("SCINTILLATIONCOMPONENT1",
                          scintEnergies, scintIntensity, nScint);
    scintMPT->AddProperty("SCINTILLATIONCOMPONENT2",
                          scintEnergies, scintIntensity, nScint);

    scintMat->SetMaterialPropertiesTable(scintMPT);

    G4Box* solidScint = new G4Box("solidScintillator",
                                  0.5 * scintSizeX,
                                  0.5 * scintSizeY,
                                  0.5 * scintThickness);
    logicScintillator =
        new G4LogicalVolume(solidScint, scintMat, "logicScintillator");

    G4double scintPosZ = goldPosZ + (slitThickness / 2.0) + (scintThickness / 2.0);
    new G4PVPlacement(0, G4ThreeVector(0. * m, offsetY, scintPosZ),
                      logicScintillator, "physScintillator",
                      logicWorld, false, 2, checkOverlaps);

    G4VisAttributes* scintVisAtt =
        new G4VisAttributes(G4Color(0.0, 1.0, 0.0, 1.0));
    scintVisAtt->SetForceSolid(true);
    logicScintillator->SetVisAttributes(scintVisAtt);

    G4OpticalSurface* scintAirSurface = new G4OpticalSurface("Scint_Air_interface");
    scintAirSurface->SetType(dielectric_dielectric);
    scintAirSurface->SetModel(unified);
    scintAirSurface->SetFinish(polished);
    scintAirSurface->SetPolish(1.0);
    new G4LogicalSkinSurface("Scint_skin", logicScintillator, scintAirSurface);

    // ========== ОПТИЧЕСКАЯ СИСТЕМА (РЕАЛЬНАЯ ЛИНЗА) ==========
    //
    // Тонкая линза:
    //   1/f = 1/u + 1/v,   M = v/u
    //   =>  f = u*M/(M+1), v = u*M
    //
    // Двояковыпуклая линза с радиусами R:
    //   1/f = 2(n-1)/R  =>  R = 2(n-1) f
    //
    // Глубина резкости (Rayleigh):
    //   DOF ≈ λ / NA²,   NA ≈ r_aperture / u
    //   => r_aperture = u * sqrt(λ / DOF)
    //
    // Для двояковыпуклой линзы центр. толщина t и апертура r_a связаны:
    //   r_a ≈ sqrt(R * t)
    //   => t ≈ r_a² / R
    //
    // Итог: при λ ≈ 550 нм, DOF = 0.3 мм, u ≈ 15 мм, M = 2.7:
    //   NA ≈ 0.043, r_a ≈ 0.64 мм, R ≈ 10.06 мм, t ≈ 40 мкм.

    G4double M = lensMagnification;
    G4double u = lensPlaneZ - scintPosZ;    // сцинтиллятор → центр линзы
    G4double f = u * M / (M + 1.0);         // фокусное расстояние
    G4double v = u * M;                     // центр линзы → плоскость изображения

    lensFocalLength = f;                    // обновим глобальную переменную

    // --- материал линзы (плавленый кварц SiO2) ---
    G4Material* lensMat = nist->FindOrBuildMaterial("G4_SILICON_DIOXIDE");
    if (!lensMat) {
        G4cerr << "ERROR: G4_SILICON_DIOXIDE not found!" << G4endl;
    }

    G4MaterialPropertiesTable* lensMPT = new G4MaterialPropertiesTable();
    const G4int nLensE = 2;
    G4double lensE[]   = { 1.5 * eV, 3.5 * eV };
    G4double lensRI[]  = { lensRefractiveIndex, lensRefractiveIndex };
    G4double lensAbs[] = { 1.0 * m, 1.0 * m };
    lensMPT->AddProperty("RINDEX",    lensE, lensRI,  nLensE);
    lensMPT->AddProperty("ABSLENGTH", lensE, lensAbs, nLensE);
    lensMat->SetMaterialPropertiesTable(lensMPT);

     // --- геометрия линзы ---
    G4double n_lens = lensRefractiveIndex;
    G4double R_lens = 2.0 * (n_lens - 1.0) * f;   // ≈ 10.06 мм
    G4double t_lens = lensCenterThickness;        // ≈ 40 мкм

    lensCurvatureRadius = R_lens;
    lensRadius          = std::sqrt(R_lens * t_lens);  // ≈ 0.63 мм

    // Центры двух сфер в системе линзы (центр линзы в z = 0):
    //   передняя сфера: z_f = t/2 - R
    //   задняя  сфера: z_b = R - t/2
    G4double z_f = t_lens / 2.0 - R_lens;
    G4double z_b = R_lens - t_lens / 2.0;

    G4Sphere* sph_f = new G4Sphere("sph_f", 0., R_lens,
                                   0., 360. * deg, 0., 180. * deg);
    G4Sphere* sph_b = new G4Sphere("sph_b", 0., R_lens,
                                   0., 360. * deg, 0., 180. * deg);

    // Пересечение двух сфер → форма двояковыпуклой линзы.
    // В Geant4 11.3.2 у 4-арг. версии НЕТ флага checkOverlaps.
    G4Transform3D trans_b(G4RotationMatrix(),
                          G4ThreeVector(0., 0., z_b - z_f));
    G4IntersectionSolid* lens_solid = new G4IntersectionSolid(
        "lens_solid", sph_f, sph_b, trans_b);

    logicLens = new G4LogicalVolume(lens_solid, lensMat, "logicLens");

    // Центр полученного solid'а в локальной системе sph_f находится
    // в точке z_local = (0 + (z_b - z_f)) / 2 = (z_b - z_f)/2.
    // Чтобы центр линзы оказался в мировом z = lensPlaneZ, смещаем
    // placement на -z_local:
    G4double z_local_center = (z_b - z_f) / 2.0;
    G4ThreeVector lensPos(0., offsetY, lensPlaneZ - z_local_center);
    new G4PVPlacement(0, lensPos, logicLens, "physLens",
                      logicWorld, false, 50, checkOverlaps);

    G4VisAttributes* lensVisAtt =
        new G4VisAttributes(G4Color(0.3, 0.8, 1.0, 0.6));
    lensVisAtt->SetForceSolid(true);
    logicLens->SetVisAttributes(lensVisAtt);

    // Оптическая поверхность линзы: диэлектрик–диэлектрик, полированная
    G4OpticalSurface* lensSurface = new G4OpticalSurface("LensSurface");
    lensSurface->SetType(dielectric_dielectric);
    lensSurface->SetModel(unified);
    lensSurface->SetFinish(polished);
    lensSurface->SetPolish(1.0);
    new G4LogicalSkinSurface("LensSkin", logicLens, lensSurface);

    // ========== КРЕМНИЕВЫЙ ДЕТЕКТОР ==========
    G4Material* siMat = nist->FindOrBuildMaterial("G4_Si");

    G4MaterialPropertiesTable* siMPT = new G4MaterialPropertiesTable();
    const G4int nSiEnergies = 3;
    G4double siEnergies[]  = { 1.5 * eV, 2.5 * eV, 3.5 * eV };
    G4double siRindex[]    = { 3.5, 4.0, 5.0 };
    G4double siAbsLength[] = { 15 * um, 10 * um, 5 * um };
    siMPT->AddProperty("RINDEX",    siEnergies, siRindex,    nSiEnergies);
    siMPT->AddProperty("ABSLENGTH", siEnergies, siAbsLength, nSiEnergies);
    siMat->SetMaterialPropertiesTable(siMPT);

    G4double detectorSizeX     = pixelSize * gridSize * M;
    G4double detectorSizeY     = slitLengthY * M;
    G4double detectorThickness = 30 * um;

    G4Box* solidDetector = new G4Box("solidDetector",
                                     0.5 * detectorSizeX,
                                     0.5 * detectorSizeY,
                                     0.5 * detectorThickness);
    logicDetector = new G4LogicalVolume(solidDetector, siMat, "logicDetector");

    G4double detectorPosZ = lensPlaneZ + v;
    new G4PVPlacement(0, G4ThreeVector(0. * m, offsetY, detectorPosZ),
                      logicDetector, "physDetector",
                      logicWorld, false, 1, false);

    G4OpticalSurface* siAirSurface = new G4OpticalSurface("Si_Air_interface");
    siAirSurface->SetType(dielectric_dielectric);
    siAirSurface->SetModel(unified);
    siAirSurface->SetFinish(polished);
    siAirSurface->SetPolish(1.0);
    new G4LogicalSkinSurface("Si_skin", logicDetector, siAirSurface);

    G4VisAttributes* siVisAtt =
        new G4VisAttributes(G4Color(0.0, 0.0, 1.0, 0.6));
    siVisAtt->SetForceSolid(true);
    logicDetector->SetVisAttributes(siVisAtt);

    // ========== ОТЛАДОЧНЫЙ ВЫВОД ==========
    G4cout << "\n=== Оптическая система (реальная линза) ===" << G4endl;
    G4cout << "M  = " << M << G4endl;
    G4cout << "u  = " << u / mm << " мм" << G4endl;
    G4cout << "v  = " << v / mm << " мм" << G4endl;
    G4cout << "f  = " << f / mm << " мм" << G4endl;
    G4cout << "R  = " << R_lens / mm << " мм" << G4endl;
    G4cout << "t  = " << t_lens / um << " мкм" << G4endl;
    G4cout << "r_a≈ " << lensRadius / mm << " мм" << G4endl;
    G4cout << "z_scint = " << scintPosZ / mm
           << " мм, z_lens = " << lensPlaneZ / mm
           << " мм, z_det = " << detectorPosZ / mm << " мм" << G4endl;
    G4cout << "==========================================\n" << G4endl;

    return physWorld;
}

void PMDetectorConstruction::ConstructSDandField()
{
    PMSensitiveDetector* sensDet = new PMSensitiveDetector("SensitiveDetector");

    if (logicDetector) {
        logicDetector->SetSensitiveDetector(sensDet);
        G4cout << "Si-детектор установлен как чувствительный" << G4endl;
    } else {
        G4cerr << "WARNING: logicDetector is null!" << G4endl;
    }

    G4SDManager::GetSDMpointer()->AddNewDetector(sensDet);
}