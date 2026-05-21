#include "PMDetectorConstruction.hh"
#include "G4PhysicalConstants.hh"
#include "G4Tubs.hh"
#include "G4SubtractionSolid.hh"

G4double leadThickness = 100. * um; //изменение толщины пластины в мкм
G4String material = "G4_Cu"; //Объявление материала

PMDetectorConstruction::PMDetectorConstruction()
{
}

PMDetectorConstruction::~PMDetectorConstruction()
{
}

G4VPhysicalVolume* PMDetectorConstruction::Construct()
{

    G4double scale = 100.;

    G4bool checkOverlaps = true;

    G4double density = universe_mean_density;                //from PhysicalConstants.h
    G4double pressure = 1.e-19 * pascal;
    G4double temperature = 0.1 * kelvin;
    new G4Material("Galactic", 1., 1.01 * g / mole, density,
        kStateGas, temperature, pressure);


    G4NistManager* nist = G4NistManager::Instance();
    G4Material* worldMat = nist->FindOrBuildMaterial("Galactic");
    G4Material* leadMat = nist->FindOrBuildMaterial(material);
    G4Material* detMat = nist->FindOrBuildMaterial("G4_SODIUM_IODIDE");

    // Оптические свойства для вакуума
    G4MaterialPropertiesTable* vacMPT = new G4MaterialPropertiesTable();
    const G4int nVac = 2;
    G4double vacEnergies[] = { 1.0 * eV, 6.0 * eV };
    G4double vacRindex[] = { 1.0, 1.0 };
    vacMPT->AddProperty("RINDEX", vacEnergies, vacRindex, nVac);
    worldMat->SetMaterialPropertiesTable(vacMPT);

    G4double xWorld = 10./scale * m;
    G4double yWorld = 10./scale * m;
    G4double zWorld = 1./3 * m;

    G4Box* solidWorld = new G4Box("solidWorld", 0.5 * xWorld, 0.5 * yWorld, 0.5 * zWorld);
    G4LogicalVolume* logicWorld = new G4LogicalVolume(solidWorld, worldMat, "logicalWorld");
    G4VPhysicalVolume* physWorld = new G4PVPlacement(0, G4ThreeVector(0., 0., 0.), logicWorld, "physWorld", 0, false, 0);

    G4double leadSize = 10.0/scale * cm;

    G4double holeRadius = 2/scale * cm;

    // Сплошная пластина (основа)
    G4Box* solidLeadBase = new G4Box("solidLeadBase", 0.5 * leadSize, 0.5 * leadSize, 0.5 * leadThickness);

    // Цилиндр для вычитания (отверстие по центру)
    G4Tubs* solidHole = new G4Tubs("solidHole", 0., holeRadius, leadThickness, 0., 360. * deg);

    // Вычитаем отверстие из пластины
    G4SubtractionSolid* solidLead = new G4SubtractionSolid("solidLead", solidLeadBase, solidHole, 0, G4ThreeVector(0., -leadSize/2., 0.));
    // -------- Создание логического и физического объёмов --------
    G4LogicalVolume* logicLead = new G4LogicalVolume(solidLead, leadMat, "logicLead");
    G4VPhysicalVolume* physLead = new G4PVPlacement(0, G4ThreeVector(0., 0., 10. * cm), logicLead, "physLead", logicWorld, false, checkOverlaps);

    // Визуализация пластины
    G4VisAttributes* leadVisAtt = new G4VisAttributes(G4Color(1.0, 0.0, 0.0, 0.5));
    leadVisAtt->SetForceSolid(true);
    logicLead->SetVisAttributes(leadVisAtt);

    // ========== СЦИНТИЛЛЯЦИОННАЯ ПЛАСТИНА ИЗ CsI ==========
    G4double csiThickness = 50 * um;
    G4double csiSizeX = 10.0/scale * cm;
    G4double csiSizeY = 5.0/scale * cm;

    // Создаём материал CsI
    G4Material* csiMat = new G4Material("CsI", 4.51 * g / cm3, 2);
    csiMat->AddElement(nist->FindOrBuildElement("Cs"), 1);
    csiMat->AddElement(nist->FindOrBuildElement("I"), 1);

    // Добавляем оптические свойства
    G4MaterialPropertiesTable* csiMPT = new G4MaterialPropertiesTable();

    const G4int nEnergies = 6;
    G4double photonEnergies[nEnergies] = { 1.91 * eV, 2.07 * eV, 2.27 * eV, 2.48 * eV, 2.76 * eV, 3.10 * eV };
    G4double refractiveIndex[nEnergies] = { 1.78, 1.79, 1.80, 1.81, 1.82, 1.83 };
    csiMPT->AddProperty("RINDEX", photonEnergies, refractiveIndex, nEnergies);

    csiMPT->AddConstProperty("SCINTILLATIONYIELD", 54000.0 / MeV);
    csiMPT->AddConstProperty("SCINTILLATIONTIMECONSTANT1", 1000.0 * ns);
    csiMPT->AddConstProperty("RESOLUTIONSCALE", 1.0);

    const G4int nScint = 7;
    G4double scintEnergies[nScint] = { 2.07 * eV, 2.18 * eV, 2.30 * eV, 2.43 * eV, 2.58 * eV, 2.76 * eV, 2.95 * eV };
    G4double scintIntensity[nScint] = { 0.05, 0.2, 0.5, 0.8, 1.0, 0.4, 0.1 };
    csiMPT->AddProperty("SCINTILLATIONCOMPONENT1", scintEnergies, scintIntensity, nScint);

    // Реалистичные значения для CsI
    const G4int nAbs = 2;
    G4double absEnergies[] = { 2.0 * eV, 3.1 * eV };
    G4double absLength[] = { 3.0 * cm, 3.0 * cm };  // ~3 см для сцинтилляционного света
    csiMPT->AddProperty("ABSLENGTH", absEnergies, absLength, nAbs);

    csiMat->SetMaterialPropertiesTable(csiMPT);

    // Создаём геометрию CsI
    G4Box* solidCsI = new G4Box("solidCsI", 0.5 * csiSizeX, 0.5 * csiSizeY, 0.5 * csiThickness);
    logicCsI = new G4LogicalVolume(solidCsI, csiMat, "logicCsI");

    // Позиция CsI (центр сцинтиллятора)
    G4double csiPosZ = 0.165 * m;
    G4VPhysicalVolume* physCsI = new G4PVPlacement(0, G4ThreeVector(0. * m, -0.025/scale * m, csiPosZ),
        logicCsI, "physCsI", logicWorld, false, 2, checkOverlaps);

    // Визуализация CsI
    G4VisAttributes* csiVisAtt = new G4VisAttributes(G4Color(0.0, 1.0, 0.0, 0.6));
    csiVisAtt->SetForceSolid(true);
    logicCsI->SetVisAttributes(csiVisAtt);

    // Создаем материал оптического клея (имитируем折射率 1.5)
    G4Material* opticalGlue = new G4Material("OpticalGlue", 1.2 * g / cm3, 1);
    opticalGlue->AddElement(nist->FindOrBuildElement("C"), 1);
    // Добавляем показатель преломления (как у стекла)
    G4MaterialPropertiesTable* glueMPT = new G4MaterialPropertiesTable();
    const G4int nGlue = 2;
    G4double glueEnergies[] = { 2.0 * eV, 3.1 * eV };
    G4double glueRindex[] = { 1.5, 1.5 };
    glueMPT->AddProperty("RINDEX", glueEnergies, glueRindex, nGlue);
    opticalGlue->SetMaterialPropertiesTable(glueMPT);

    // Создаем объем клея (толщина 10 микрон)
    G4double glueThickness = 10.0 * um;
    G4Box* solidGlue = new G4Box("solidGlue",
        0.5 * csiSizeX,
        0.5 * csiSizeY,
        0.5 * glueThickness);
    G4LogicalVolume* logicGlue = new G4LogicalVolume(solidGlue, opticalGlue, "logicGlue");

    // Размещаем клей между CsI и детектором
    G4double gluePosZ = csiPosZ + (csiThickness / 2.0) + (glueThickness / 2.0);
    new G4PVPlacement(0, G4ThreeVector(0. * m, -0.025 / scale * m, gluePosZ),
        logicGlue, "physGlue", logicWorld, false, 3, checkOverlaps);

    

    // ========== КРЕМНИЕВЫЙ ДЕТЕКТОР (ВПЛОТНУЮ К CsI) ==========
    G4Material* siMat = nist->FindOrBuildMaterial("G4_Si");

    // Оптические свойства для кремния
    G4MaterialPropertiesTable* siMPT = new G4MaterialPropertiesTable();

    const G4int nSiEnergies = 3;
    G4double siEnergies[] = { 1.5 * eV, 2.5 * eV, 3.5 * eV };
    G4double siRindex[] = { 3.5, 4.0, 5.0 };        // Показатель преломления кремния
    G4double siAbsLength[] = { 500 * um, 50 * um, 10 * um }; // Длина поглощения

    siMPT->AddProperty("RINDEX", siEnergies, siRindex, nSiEnergies);
    siMPT->AddProperty("ABSLENGTH", siEnergies, siAbsLength, nSiEnergies);

    // Квантовая эффективность кремния
    G4double siEfficiency[] = { 0.5, 0.8, 0.9 };
    siMPT->AddProperty("EFFICIENCY", siEnergies, siEfficiency, nSiEnergies);

    siMat->SetMaterialPropertiesTable(siMPT);

    // Создаем кремниевый детектор (такого же размера как CsI)
    G4double detectorSizeX = 10.0/scale * cm;
    G4double detectorSizeY = 5.0/scale * cm;
    G4double detectorThickness = 0.5 * mm;

    G4Box* solidDetector = new G4Box("solidDetector",
        0.5 * detectorSizeX,
        0.5 * detectorSizeY,
        0.5 * detectorThickness);
    logicDetector = new G4LogicalVolume(solidDetector, siMat, "logicDetector");

    // Изменяем позицию детектора (теперь после клея)
    G4double detectorPosZ = gluePosZ + (glueThickness / 2.0) + (detectorThickness / 2.0);

    G4VPhysicalVolume* physDetector = new G4PVPlacement(0,
        G4ThreeVector(0. * m, -0.025/scale * m, detectorPosZ),
        logicDetector, "physDetector", logicWorld, false, 1, checkOverlaps);

    // Визуализация детектора
    G4VisAttributes* siVisAtt = new G4VisAttributes(G4Color(0.0, 0.0, 1.0, 0.6));
    siVisAtt->SetForceSolid(true);
    logicDetector->SetVisAttributes(siVisAtt);

    // ========== ОПТИЧЕСКАЯ ПОВЕРХНОСТЬ МЕЖДУ CsI И Si ==========
// Создаем MaterialPropertiesTable для поверхности
    G4MaterialPropertiesTable* surfaceMPT = new G4MaterialPropertiesTable();

    // КОММЕНТАРИЙ: Не задаем REFLECTIVITY и TRANSMITTANCE вручную,
    // позволяем Geant4 рассчитывать их по формулам Френеля из показателей преломления

    /*
    const G4int nInterfEnergies = 3;
    G4double interfEnergies[] = { 1.5 * eV, 2.5 * eV, 3.5 * eV };
    G4double reflectivity[] = { 0.05, 0.05, 0.05 };
    G4double transmittance[] = { 0.95, 0.95, 0.95 };

    surfaceMPT->AddProperty("REFLECTIVITY", interfEnergies, reflectivity, nInterfEnergies);
    surfaceMPT->AddProperty("TRANSMITTANCE", interfEnergies, transmittance, nInterfEnergies);
    */

    // Создаем оптическую поверхность
    G4OpticalSurface* csSiInterface = new G4OpticalSurface("CsI_Si_interface");
    csSiInterface->SetType(dielectric_dielectric);
    csSiInterface->SetModel(unified);
    csSiInterface->SetFinish(polished);

    // Явно задаем идеальную гладкость (подавляем любое рассеяние)
    csSiInterface->SetPolish(1.0);  // 1.0 = идеально гладкая

    // Присоединяем таблицу свойств к поверхности
    csSiInterface->SetMaterialPropertiesTable(surfaceMPT);

    // Применяем поверхность к границе между CsI и детектором
    new G4LogicalBorderSurface("CsI_Si_border", physCsI, physDetector, csSiInterface);

    return physWorld;
}

void PMDetectorConstruction::ConstructSDandField()
{
    PMSensitiveDetector* sensDet = new PMSensitiveDetector("SensitveDetector");


    if (logicDetector) {
        logicDetector->SetSensitiveDetector(sensDet);
        G4cout << "Main detector set as sensitive detector" << G4endl;
    }
    else {
        G4cerr << "WARNING: logicDetector is null!" << G4endl;
    }

    G4SDManager::GetSDMpointer()->AddNewDetector(sensDet);
}