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

    G4double xWorld = 3./scale * m;
    G4double yWorld = 3./scale * m;
    G4double zWorld = 1./3 * m;

    G4Box* solidWorld = new G4Box("solidWorld", 0.5 * xWorld, 0.5 * yWorld, 0.5 * zWorld);
    G4LogicalVolume* logicWorld = new G4LogicalVolume(solidWorld, worldMat, "logicalWorld");
    G4VPhysicalVolume* physWorld = new G4PVPlacement(0, G4ThreeVector(0., 0., 0.), logicWorld, "physWorld", 0, false, 0);

    // ========== ПЛАСТИНА С КОРОТКИМИ ЩЕЛЯМИ ДЛЯ MTF ==========
    G4double leadSize = 10.0 / scale * cm;      // 1 мм

    // Создаём цельную пластину
    G4Box* solidLeadBase = new G4Box("solidLeadBase",
        0.5 * leadSize,
        0.5 * leadSize,
        0.5 * leadThickness);

    // Структура для определения щели
    struct SlitDef {
        G4double width;    // ширина щели (по Y) - мкм
        G4double length;   // длина щели (по X) - мкм (КОРОТКАЯ!)
        G4double x;        // центр по X (мм)
        G4double y;        // центр по Y (мм)
    };

    // ПРАВИЛЬНЫЕ щели для MTF (короткие, не доходят до краёв)
    // Все щели в центре пластины, разные Y позиции
    std::vector<SlitDef> slits = {
        // Щель 90 мкм (на грани разрешения)
        {90.0 * um, 400.0 * um, 0.0 * mm, -0.250 * mm},

        // Щель 110 мкм (должна разрешаться)
        {110.0 * um, 400.0 * um, 0.0 * mm, 0.000 * mm},

        // Щель 130 мкм (должна разрешаться хорошо)
        {130.0 * um, 400.0 * um, 0.0 * mm, 0.250 * mm},
    };

    // Начинаем с цельной пластины
    G4VSolid* currentSolid = solidLeadBase;

    // Последовательно вычитаем щели
    for (size_t i = 0; i < slits.size(); ++i) {
        const auto& s = slits[i];

        // Прямоугольная щель (короткая по X, узкая по Y)
        G4Box* slitBox = new G4Box(G4String("slit") + std::to_string(i),
            0.5 * s.length,   // длина по X (короткая!)
            0.5 * s.width,    // ширина по Y
            0.5 * leadThickness);

        // Позиция щели
        G4ThreeVector pos(s.x, s.y, 0.0);

        // Вычитаем
        currentSolid = new G4SubtractionSolid(G4String("solidLead") + std::to_string(i),
            currentSolid, slitBox, 0, pos);
    }

    // Создаём логический объём
    G4LogicalVolume* logicLead = new G4LogicalVolume(currentSolid, leadMat, "logicLead");

    // Размещаем пластину
    G4VPhysicalVolume* physLead = new G4PVPlacement(0,
        G4ThreeVector(0., 0., 10. * cm),
        logicLead,
        "physLead",
        logicWorld,
        false,
        0,
        checkOverlaps);

    // Визуализация (красная, полупрозрачная)
    G4VisAttributes* leadVisAtt = new G4VisAttributes(G4Color(1.0, 0.0, 0.0, 0.6));
    leadVisAtt->SetForceSolid(true);
    logicLead->SetVisAttributes(leadVisAtt);

    // Отладочная информация
    G4cout << "\n=== МЕДНАЯ ПЛАСТИНА С 3 ЩЕЛЯМИ ===" << G4endl;
    G4cout << "Размер: " << leadSize / mm << " x " << leadSize / mm << " mm" << G4endl;
    G4cout << "Толщина: " << leadThickness / um << " um" << G4endl;
    G4cout << "Щели (ширина x длина, позиция Y):" << G4endl;
    for (const auto& s : slits) {
        G4cout << "  - " << s.width / um << " x " << s.length / mm << " мм, Y = " << s.y / mm << " мм" << G4endl;
    }
    G4cout << "==================================\n" << G4endl;

    // ========== СЦИНТИЛЛЯЦИОННАЯ ПЛАСТИНА ИЗ CsI ==========
    G4double csiThickness = fCsIThickness;  // 10-500 мкм
    G4double csiSizeX = 10.0 / scale * cm;
    G4double csiSizeY = 10.0 / scale * cm;

    // Создаём материал CsI (без изменений)
    G4Material* csiMat = new G4Material("CsI", 4.51 * g / cm3, 2);
    csiMat->AddElement(nist->FindOrBuildElement("Cs"), 1);
    csiMat->AddElement(nist->FindOrBuildElement("I"), 1);

    // Оптические свойства (без изменений)
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

    // Длина поглощения
    const G4int nAbs = 2;
    G4double absEnergies[] = { 2.0 * eV, 3.1 * eV };
    G4double absLength1 = std::max(50.0 * um, csiThickness * 0.2);
    G4double absLength2 = std::max(50.0 * um, csiThickness * 0.2);
    G4double absLength[] = { absLength1, absLength2 };
    csiMPT->AddProperty("ABSLENGTH", absEnergies, absLength, nAbs);

    csiMat->SetMaterialPropertiesTable(csiMPT);

    // Создаём геометрию CsI
    G4Box* solidCsI = new G4Box("solidCsI", 0.5 * csiSizeX, 0.5 * csiSizeY, 0.5 * csiThickness);
    logicCsI = new G4LogicalVolume(solidCsI, csiMat, "logicCsI");

    // ========== ИСПРАВЛЕНО: позиция CsI по центру (Y = 0) ==========
    G4double csiPosZ = 0.165 * m;
    G4VPhysicalVolume* physCsI = new G4PVPlacement(0, G4ThreeVector(0. * m, 0. * m, csiPosZ),
        logicCsI, "physCsI", logicWorld, false, 2, checkOverlaps);

    //// ========== ОТРАЖАТЕЛЬ (без изменений) ==========
    //G4OpticalSurface* reflector = new G4OpticalSurface("CsI_Reflector");
    //reflector->SetType(dielectric_metal);
    //reflector->SetModel(unified);
    //reflector->SetFinish(polished);
    //reflector->SetPolish(1.0);

    //G4MaterialPropertiesTable* reflectorMPT = new G4MaterialPropertiesTable();
    //const G4int nRefl = 2;
    //G4double reflEnergies[] = { 2.0 * eV, 3.1 * eV };
    //G4double reflectivity[] = { 0.90, 0.90 };
    //reflectorMPT->AddProperty("REFLECTIVITY", reflEnergies, reflectivity, nRefl);
    //reflector->SetMaterialPropertiesTable(reflectorMPT);

    //new G4LogicalSkinSurface("CsI_Reflector_Surface", logicCsI, reflector);

    // Визуализация CsI
    G4VisAttributes* csiVisAtt = new G4VisAttributes(G4Color(0.0, 1.0, 0.0, 0.6));
    csiVisAtt->SetForceSolid(true);
    logicCsI->SetVisAttributes(csiVisAtt);

    // ========== ОПТИЧЕСКИЙ КЛЕЙ ==========
    G4Material* opticalGlue = new G4Material("OpticalGlue", 1.2 * g / cm3, 1);
    opticalGlue->AddElement(nist->FindOrBuildElement("C"), 1);
    G4MaterialPropertiesTable* glueMPT = new G4MaterialPropertiesTable();
    const G4int nGlue = 2;
    G4double glueEnergies[] = { 2.0 * eV, 3.1 * eV };
    G4double glueRindex[] = { 1.5, 1.5 };
    glueMPT->AddProperty("RINDEX", glueEnergies, glueRindex, nGlue);
    opticalGlue->SetMaterialPropertiesTable(glueMPT);

    G4double glueThickness = 1.0 * um;
    G4Box* solidGlue = new G4Box("solidGlue",
        0.5 * csiSizeX,
        0.5 * csiSizeY,
        0.5 * glueThickness);
    G4LogicalVolume* logicGlue = new G4LogicalVolume(solidGlue, opticalGlue, "logicGlue");

    G4double gluePosZ = csiPosZ + (csiThickness / 2.0) + (glueThickness / 2.0);
    // ========== ИСПРАВЛЕНО: позиция клея по центру (Y = 0) ==========
    G4VPhysicalVolume* physGlue = new G4PVPlacement(0, G4ThreeVector(0. * m, 0. * m, gluePosZ),
        logicGlue, "physGlue", logicWorld, false, 3, checkOverlaps);

    // ========== КРЕМНИЕВЫЙ ДЕТЕКТОР ==========
    G4Material* siMat = nist->FindOrBuildMaterial("G4_Si");

    G4MaterialPropertiesTable* siMPT = new G4MaterialPropertiesTable();

    const G4int nSiEnergies = 3;
    G4double siEnergies[] = { 1.5 * eV, 2.5 * eV, 3.5 * eV };
    G4double siRindex[] = { 3.5, 4.0, 5.0 };
    G4double siAbsLength[] = { 15 * um, 10 * um, 5 * um };
    siMPT->AddProperty("RINDEX", siEnergies, siRindex, nSiEnergies);
    siMPT->AddProperty("ABSLENGTH", siEnergies, siAbsLength, nSiEnergies);
    siMat->SetMaterialPropertiesTable(siMPT);

    G4double detectorSizeX = 10.0 / scale * cm;
    G4double detectorSizeY = 10.0 / scale * cm;
    G4double detectorThickness = 30 * um;

    G4Box* solidDetector = new G4Box("solidDetector",
        0.5 * detectorSizeX,
        0.5 * detectorSizeY,
        0.5 * detectorThickness);
    logicDetector = new G4LogicalVolume(solidDetector, siMat, "logicDetector");

    G4double detectorPosZ = gluePosZ + (glueThickness / 2.0) + (detectorThickness / 2.0);
    // ========== ИСПРАВЛЕНО: позиция детектора по центру (Y = 0) ==========
    G4VPhysicalVolume* physDetector = new G4PVPlacement(0,
        G4ThreeVector(0. * m, 0. * m, detectorPosZ),
        logicDetector, "physDetector", logicWorld, false, 1, checkOverlaps);

    // Визуализация детектора
    G4VisAttributes* siVisAtt = new G4VisAttributes(G4Color(0.0, 0.0, 1.0, 0.6));
    siVisAtt->SetForceSolid(true);
    logicDetector->SetVisAttributes(siVisAtt);

    // ========== ОПТИЧЕСКИЕ ПОВЕРХНОСТИ (без изменений) ==========
    G4OpticalSurface* csiGlueInterface = new G4OpticalSurface("CsI_Glue_interface");
    csiGlueInterface->SetType(dielectric_dielectric);
    csiGlueInterface->SetModel(unified);
    csiGlueInterface->SetFinish(polished);
    csiGlueInterface->SetPolish(1.0);
    new G4LogicalBorderSurface("CsI_Glue_border", physCsI, physGlue, csiGlueInterface);

    G4OpticalSurface* glueSiInterface = new G4OpticalSurface("Glue_Si_interface");
    glueSiInterface->SetType(dielectric_dielectric);
    glueSiInterface->SetModel(unified);
    glueSiInterface->SetFinish(polished);
    glueSiInterface->SetPolish(1.0);
    new G4LogicalBorderSurface("Glue_Si_border", physGlue, physDetector, glueSiInterface);

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