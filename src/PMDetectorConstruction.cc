#include "PMDetectorConstruction.hh"
#include "G4PhysicalConstants.hh"
#include "G4Tubs.hh"
#include "G4SubtractionSolid.hh"
#include "global_parameters.hh"
#include <vector>
#include <iostream>

G4String material = "G4_Au"; //Золото

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

    // ========== ЗОЛОТЫЕ ПОЛОСКИ ВМЕСТО МЕДНОЙ ПЛАСТИНЫ ==========
    G4double leadSize = pixelSize * gridSize;
    G4double slitThickness = slitWidth;  // толщина = ширине
    G4double slitPeriod = slitWidth + slitWidth;  // шаг полоски
    G4double slitLengthY = leadSize;  // теперь на всю длину и ширину

    // Количество полосок
    G4int numSlits = (G4int)(leadSize / slitPeriod);

    // Рассчитываем общую ширину для центровки
    G4double totalWidth = numSlits * slitPeriod;
    G4double startX = -totalWidth / 2.0 + slitWidth / 2.0;

    // Материал золота
    G4Material* goldMat = nist->FindOrBuildMaterial("G4_Au");

    // Создаём одну полоску
    G4Box* solidSlit = new G4Box("solidSlit",
        0.5 * slitWidth,
        0.5 * slitLengthY,
        0.5 * slitThickness);

    // Создаём логический объём
    G4LogicalVolume* logicLead = new G4LogicalVolume(solidSlit, goldMat, "logicLead");

    // Визуализация (золотой цвет)
    G4VisAttributes* leadVisAtt = new G4VisAttributes(G4Color(1.0, 0.84, 0.0, 0.8));
    leadVisAtt->SetForceSolid(true);
    logicLead->SetVisAttributes(leadVisAtt);

    // Отладочная информация
    G4cout << "\n=== ЗОЛОТЫЕ ПОЛОСКИ ===" << G4endl;
    G4cout << "Размер области: " << leadSize / mm << " x " << leadSize / mm << " mm" << G4endl;
    G4cout << "Полосок: " << numSlits << G4endl;
    G4cout << "Ширина полоски: " << slitWidth / um << " мкм" << G4endl;
    G4cout << "Толщина: " << slitThickness / um << " мкм" << G4endl;
    G4cout << "Зазор между полосками: " << slitWidth / um << " мкм" << G4endl;
    G4cout << "Длина полоски по Y: " << slitLengthY / um << " мкм" << G4endl;
    G4cout << "========================\n" << G4endl;

    // ========== ВЫБОР СЦИНТИЛЛЯТОРА ==========
    G4double csiThickness = fCsIThickness;
    G4double csiSizeX = pixelSize * gridSize;
    G4double csiSizeY = pixelSize * gridSize;

    G4Material* csiMat = nullptr;
    G4cout << "\n=== Выбор сцинтиллятора ===" << G4endl;

    if (scintillatorType == 0) {
        // --- CsI(Tl) ---
        G4cout << "Используется: CsI(Tl)" << G4endl;
        csiMat = new G4Material("CsI_Tl", 4.51 * g/cm3, 2);
        csiMat->AddElement(nist->FindOrBuildElement("Cs"), 1);
        csiMat->AddElement(nist->FindOrBuildElement("I"), 1);

        G4MaterialPropertiesTable* csiMPT = new G4MaterialPropertiesTable();

        // RINDEX
        const G4int nRI = 2;
        G4double riEnergies[] = { 1.77 * eV, 4.13 * eV };
        G4double refractiveIndex[] = { 1.79, 1.79 };
        csiMPT->AddProperty("RINDEX", riEnergies, refractiveIndex, nRI);

        // ABSLENGTH
        const G4int nAbs = 2;
        G4double absEnergies[] = { 1.77 * eV, 4.13 * eV };
        G4double absLength[] = { 30.0 * cm, 30.0 * cm };
        csiMPT->AddProperty("ABSLENGTH", absEnergies, absLength, nAbs);

        // SCINTILLATION
        csiMPT->AddConstProperty("SCINTILLATIONYIELD", 52000.0 / MeV);
        csiMPT->AddConstProperty("RESOLUTIONSCALE", 1.0);
        csiMPT->AddConstProperty("SCINTILLATIONTIMECONSTANT1", 68.0 * ns);
        csiMPT->AddConstProperty("SCINTILLATIONYIELD1", 0.07);
        csiMPT->AddConstProperty("SCINTILLATIONTIMECONSTANT2", 950.0 * ns);
        csiMPT->AddConstProperty("SCINTILLATIONYIELD2", 0.93);

        // SPECTRUM
        const G4int nScint = 9;
        G4double scintEnergies[] = { 2.00*eV, 2.10*eV, 2.20*eV, 2.25*eV, 2.30*eV, 2.40*eV, 2.50*eV, 2.70*eV, 2.90*eV };
        G4double scintIntensity[] = { 0.10, 0.40, 0.85, 1.00, 0.90, 0.60, 0.30, 0.15, 0.05 };
        csiMPT->AddProperty("SCINTILLATIONCOMPONENT1", scintEnergies, scintIntensity, nScint);
        csiMPT->AddProperty("SCINTILLATIONCOMPONENT2", scintEnergies, scintIntensity, nScint);

        csiMat->SetMaterialPropertiesTable(csiMPT);

    } else {
        // --- YAG(Tb) ---
        G4cout << "Используется: YAG(Tb)" << G4endl;
        csiMat = new G4Material("YAG_Tb", 4.55 * g/cm3, 4);
        csiMat->AddElement(nist->FindOrBuildElement("Y"),  3);
        csiMat->AddElement(nist->FindOrBuildElement("Al"), 5);
        csiMat->AddElement(nist->FindOrBuildElement("O"), 12);
        csiMat->AddElement(nist->FindOrBuildElement("Tb"), 1); // легирующая примесь

        G4MaterialPropertiesTable* csiMPT = new G4MaterialPropertiesTable();

        // RINDEX
        const G4int nRI = 2;
        G4double riEnergies[] = { 1.77 * eV, 4.13 * eV };
        G4double refractiveIndex[] = { 1.84, 1.84 };
        csiMPT->AddProperty("RINDEX", riEnergies, refractiveIndex, nRI);

        // ABSLENGTH
        const G4int nAbs = 2;
        G4double absEnergies[] = { 1.77 * eV, 4.13 * eV };
        G4double absLength[] = { 40.0 * cm, 40.0 * cm };
        csiMPT->AddProperty("ABSLENGTH", absEnergies, absLength, nAbs);

        // SCINTILLATION
        csiMPT->AddConstProperty("SCINTILLATIONYIELD", 28000.0 / MeV);
        csiMPT->AddConstProperty("RESOLUTIONSCALE", 1.0);
        csiMPT->AddConstProperty("SCINTILLATIONTIMECONSTANT1", 65.0 * ns);
        csiMPT->AddConstProperty("SCINTILLATIONYIELD1", 0.85);
        csiMPT->AddConstProperty("SCINTILLATIONTIMECONSTANT2", 160.0 * ns);
        csiMPT->AddConstProperty("SCINTILLATIONYIELD2", 0.15);

        // SPECTRUM (пик ~530-545 нм = 2.28-2.32 эВ)
        const G4int nScint = 9;
        G4double scintEnergies[] = { 2.00*eV, 2.10*eV, 2.20*eV, 2.25*eV, 2.30*eV, 2.35*eV, 2.50*eV, 2.70*eV, 2.90*eV };
        G4double scintIntensity[] = { 0.05, 0.20, 0.60, 0.90, 1.00, 0.95, 0.40, 0.10, 0.02 };
        csiMPT->AddProperty("SCINTILLATIONCOMPONENT1", scintEnergies, scintIntensity, nScint);
        csiMPT->AddProperty("SCINTILLATIONCOMPONENT2", scintEnergies, scintIntensity, nScint);

        csiMat->SetMaterialPropertiesTable(csiMPT);
    }

    // ========== КРИСТАЛЛ И ГЕОМЕТРИЯ СЦИНТИЛЛЯТОРА ==========
    G4Box* solidCsI = new G4Box("solidCsI", 0.5 * csiSizeX, 0.5 * csiSizeY, 0.5 * csiThickness);
    logicCsI = new G4LogicalVolume(solidCsI, csiMat, "logicCsI");

    // Позиция CsI: на расстоянии 10 см от нуля по Z
    G4double csiPosZ = 10.0 * cm;
    G4VPhysicalVolume* physCsI = new G4PVPlacement(0, G4ThreeVector(0. * m, 0. * m, csiPosZ),
        logicCsI, "physCsI", logicWorld, false, 2, checkOverlaps);

    // ========== ОТРАЖАТЕЛЬ (диффузный или зеркальный) ==========
    G4OpticalSurface* reflector = new G4OpticalSurface("CsI_Reflector");
    reflector->SetType(dielectric_metal);      // Оставляем как есть
    reflector->SetModel(unified);
    reflector->SetFinish(polished);            // Или ground для диффузного отражения
    reflector->SetPolish(0.8);                 // Не идеально полированный

    G4MaterialPropertiesTable* reflectorMPT = new G4MaterialPropertiesTable();
    const G4int nRefl = 2;
    G4double reflEnergies[] = { 1.77 * eV, 4.13 * eV };
    G4double reflectivity[] = { 0.95, 0.95 };  // 95% отражения (Teflon имеет ~95-98%)
    reflectorMPT->AddProperty("REFLECTIVITY", reflEnergies, reflectivity, nRefl);
    reflector->SetMaterialPropertiesTable(reflectorMPT);

    //new G4LogicalSkinSurface("CsI_Reflector_Surface", logicCsI, reflector);

    // Визуализация CsI
    G4VisAttributes* csiVisAtt = new G4VisAttributes(G4Color(0.0, 1.0, 0.0, 0.6));
    csiVisAtt->SetForceSolid(true);
    logicCsI->SetVisAttributes(csiVisAtt);

    // ========== ЗОЛОТЫЕ ПОЛОСКИ ПРЯМО НА СЦИНТИЛЛЯТОРЕ ==========
    // Размещаем полоски вплотную к верхней грани CsI, строго над ним
    G4double goldPosZ = csiPosZ + csiThickness / 2.0 + 1.0 * nm;  // 1 нм зазор

    // Центрируем полоски по Y относительно CsI
    G4double offsetY = (csiSizeY - slitLengthY) / 2.0;

    for (G4int i = 0; i < numSlits; ++i) {
        G4double x = startX + i * slitPeriod;
        // checkOverlaps=false, так как полоски вплотную к CsI
        new G4PVPlacement(0, G4ThreeVector(x, offsetY, goldPosZ),
            logicLead, "physSlit" + std::to_string(i), logicWorld, false, i, false);
    }

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
        0.5 * slitLengthY,  // Используем ту же длину по Y, что и полоски
        0.5 * glueThickness);
    G4LogicalVolume* logicGlue = new G4LogicalVolume(solidGlue, opticalGlue, "logicGlue");

    G4double gluePosZ = csiPosZ + (csiThickness / 2.0) + (glueThickness / 2.0);
    G4double glueOffsetY = (csiSizeY - slitLengthY) / 2.0;  // Центрируем по Y
    G4VPhysicalVolume* physGlue = new G4PVPlacement(0, G4ThreeVector(0. * m, glueOffsetY, gluePosZ),
        logicGlue, "physGlue", logicWorld, false, 3, false);  // checkOverlaps=false

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

    G4double detectorSizeX = pixelSize * gridSize;
    G4double detectorSizeY = slitLengthY;  // Используем ту же длину по Y, что и полоски
    G4double detectorThickness = 30 * um;

    G4Box* solidDetector = new G4Box("solidDetector",
        0.5 * detectorSizeX,
        0.5 * detectorSizeY,
        0.5 * detectorThickness);
    logicDetector = new G4LogicalVolume(solidDetector, siMat, "logicDetector");

    G4double detectorPosZ = gluePosZ + (glueThickness / 2.0) + (detectorThickness / 2.0);
    G4VPhysicalVolume* physDetector = new G4PVPlacement(0,
        G4ThreeVector(0. * m, glueOffsetY, detectorPosZ),  // Центрируем по Y
        logicDetector, "physDetector", logicWorld, false, 1, false);  // checkOverlaps=false

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