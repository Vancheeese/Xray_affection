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

G4VPhysicalVolume *PMDetectorConstruction::Construct()
{
    G4bool checkOverlaps = true;

    G4double density = universe_mean_density;                //from PhysicalConstants.h
    G4double pressure = 1.e-19 * pascal;
    G4double temperature = 0.1 * kelvin;
    new G4Material("Galactic", 1., 1.01 * g / mole, density,
        kStateGas, temperature, pressure);


    G4NistManager *nist  = G4NistManager::Instance();
    G4Material *worldMat = nist->FindOrBuildMaterial("Galactic");
    G4Material *leadMat = nist->FindOrBuildMaterial(material);       
    G4Material *detMat = nist->FindOrBuildMaterial("G4_SODIUM_IODIDE");


    G4double xWorld = 1. * m;
    G4double yWorld = 1. * m;
    G4double zWorld = 1. * m;

    G4Box *solidWorld = new G4Box("solidWorld", 0.5 * xWorld, 0.5 * yWorld, 0.5 * zWorld);
    G4LogicalVolume *logicWorld = new G4LogicalVolume(solidWorld, worldMat, "logicalWorld");
    G4VPhysicalVolume *physWorld = new G4PVPlacement(0, G4ThreeVector(0., 0., 0.), logicWorld, "physWorld", 0, false, 0);
           
    G4double leadSize = 10.0 * cm;

    // Основное тело (сплошная пластина)
    G4Box* solidLeadBase = new G4Box("solidLeadBase", 0.5 * leadSize, 0.5 * leadSize, 0.5 * leadThickness);

    // Общие параметры для всех полос
    G4double slitLength = 1.0 * cm;            // длина (по X)
    G4double gapBetweenSlits = 0.5 * mm;       // расстояние между полосами в одной группе (по Y)
    G4double slitHalfZ = 0.5 * leadThickness + 0.1 * mm; // запас по Z для сквозного вырезания

    // Левый нижний угол пластины (центр пластины в (0,0,0))
    G4double leftBottomX = -0.5 * leadSize;
    G4double leftBottomY = -0.5 * leadSize;

    // Отступ от левого нижнего угла для начала первой полосы
    G4double offsetFromCorner = 0.8 * cm;

    // Начальная точка по Y для всех полос (одинаковая для обеих групп)
    G4double startY = leftBottomY + offsetFromCorner;

    // -------- Первая группа: 10 полос, ширина 0.5 мм --------
    G4int nSlitsGroup1 = 10;
    G4double slitWidth1 = 0.5 * mm;

    // Стартовая X для первой группы (левый край первой полосы)
    G4double startX1 = leftBottomX + offsetFromCorner;

    // Текущее составное тело (начинаем с основного)
    G4VSolid* solidLeadWithSlits = solidLeadBase;

    // Вырезаем первую группу
    for (int i = 0; i < nSlitsGroup1; ++i) {
        // Левый нижний угол i-й полосы
        G4double slitLowX = startX1;
        G4double slitLowY = startY + i * (slitWidth1 + gapBetweenSlits);
        // Центр полосы
        G4double slitCenterX = slitLowX + 0.5 * slitLength;
        G4double slitCenterY = slitLowY + 0.5 * slitWidth1;

        G4Box* slitBox = new G4Box("slit1_" + std::to_string(i), 0.5 * slitLength, 0.5 * slitWidth1, slitHalfZ);
        G4Transform3D transform = G4Translate3D(slitCenterX, slitCenterY, 0.0);
        solidLeadWithSlits = new G4SubtractionSolid("leadWithSlits1_" + std::to_string(i), solidLeadWithSlits, slitBox, transform);
    }

    // -------- Вторая группа: 6 полос, ширина 0.9 мм, расстояние между полосами = ширине (0.9 мм) --------
    G4int nSlitsGroup2 = 6;
    G4double slitWidth2 = 0.9 * mm;
    G4double stepY2 = slitWidth2 + slitWidth2;   // шаг по Y (ширина + зазор = 0.9+0.9)

    // Правый край первой группы полос
    G4double rightEdgeGroup1 = startX1 + slitLength;   // предполагается, что startX1 и slitLength определены ранее
    G4double gapToRight = 0.8 * cm;
    G4double startX2 = rightEdgeGroup1 + gapToRight;

    // Вырезаем вторую группу
    for (int i = 0; i < nSlitsGroup2; ++i) {
        G4double slitLowX = startX2;
        G4double slitLowY = startY + i * stepY2;      // вертикальный шаг = 2 * ширина
        G4double slitCenterX = slitLowX + 0.5 * slitLength;
        G4double slitCenterY = slitLowY + 0.5 * slitWidth2;

        G4Box* slitBox = new G4Box("slit2_" + std::to_string(i), 0.5 * slitLength, 0.5 * slitWidth2, slitHalfZ);
        G4Transform3D transform = G4Translate3D(slitCenterX, slitCenterY, 0.0);
        solidLeadWithSlits = new G4SubtractionSolid("leadWithSlits2_" + std::to_string(i), solidLeadWithSlits, slitBox, transform);
    }

    // -------- Третья группа: 6 полос, ширина 1.0 мм, расстояние между полосами = ширине (1.0 мм) --------
    G4int nSlitsGroup3 = 6;                // количество полос в третьей группе
    G4double slitWidth3 = 1.0 * mm;        // ширина полосы
    G4double stepY3 = slitWidth3 + slitWidth3;   // шаг по Y: ширина + зазор = 2*ширина

    // Правый край второй группы полос (предполагается, что startX2 и slitLength определены ранее)
    G4double rightEdgeGroup2 = startX2 + slitLength;   // правый край второй группы
    G4double gapToRight2 = 0.8 * cm;                  // расстояние от правого края второй группы до левого края третьей
    G4double startX3 = rightEdgeGroup2 + gapToRight2; // стартовая X для третьей группы

    // Вырезаем третью группу
    for (int i = 0; i < nSlitsGroup3; ++i) {
        G4double slitLowX = startX3;
        G4double slitLowY = startY + i * stepY3;      // вертикальный шаг
        G4double slitCenterX = slitLowX + 0.5 * slitLength;
        G4double slitCenterY = slitLowY + 0.5 * slitWidth3;

        G4Box* slitBox = new G4Box("slit3_" + std::to_string(i), 0.5 * slitLength, 0.5 * slitWidth3, slitHalfZ);
        G4Transform3D transform = G4Translate3D(slitCenterX, slitCenterY, 0.0);
        solidLeadWithSlits = new G4SubtractionSolid("leadWithSlits3_" + std::to_string(i), solidLeadWithSlits, slitBox, transform);
    }

    // -------- Четвертая группа: 6 полос, ширина 2.0 мм, расстояние между полосами = ширине (2.0 мм) --------
    G4int nSlitsGroup4 = 6;                // количество полос в четвертой группе
    G4double slitWidth4 = 2.0 * mm;        // ширина полосы
    G4double stepY4 = slitWidth4 + slitWidth4;   // шаг по Y: ширина + зазор (= 2*ширина)

    // Правый край третьей группы полос (предполагается, что startX3 и slitLength определены ранее)
    G4double rightEdgeGroup3 = startX3 + slitLength;
    G4double gapToRight3 = 0.8 * cm;                  // отступ от правого края третьей группы
    G4double startX4 = rightEdgeGroup3 + gapToRight3;

    // Вырезаем четвертую группу
    for (int i = 0; i < nSlitsGroup4; ++i) {
        G4double slitLowX = startX4;
        G4double slitLowY = startY + i * stepY4;
        G4double slitCenterX = slitLowX + 0.5 * slitLength;
        G4double slitCenterY = slitLowY + 0.5 * slitWidth4;

        G4Box* slitBox = new G4Box("slit4_" + std::to_string(i), 0.5 * slitLength, 0.5 * slitWidth4, slitHalfZ);
        G4Transform3D transform = G4Translate3D(slitCenterX, slitCenterY, 0.0);
        solidLeadWithSlits = new G4SubtractionSolid("leadWithSlits4_" + std::to_string(i), solidLeadWithSlits, slitBox, transform);
    }

    // -------- Создание логического и физического объёмов --------
    G4LogicalVolume* logicLead = new G4LogicalVolume(solidLeadWithSlits, leadMat, "logicLead");
    G4VPhysicalVolume* physLead = new G4PVPlacement(0, G4ThreeVector(0., 0., 10. * cm), logicLead, "physLead", logicWorld, false, checkOverlaps);

    // Визуализация
    G4VisAttributes* leadVisAtt = new G4VisAttributes(G4Color(1.0, 0.0, 0.0, 0.5));
    leadVisAtt->SetForceSolid(true);
    logicLead->SetVisAttributes(leadVisAtt);




    G4double detectorSize = 10.0 * cm;

   /* G4Box *solidDetector = new G4Box("solidDetector", 0.005*m, 0.005*m, 0.001*m);
    logicDetector = new G4LogicalVolume(solidDetector, worldMat, "logicDetector");
        for (G4int i=0; i<50; i++)
        {
            for (G4int j=0; j<50; j++)
            {
                G4VPhysicalVolume *physDetector = new G4PVPlacement(0, G4ThreeVector(-0.2525*m+(i+0.5)*m/100, -0.2525*m+(j+0.5)*m/100 , 0.19 *m), logicDetector, "physDetector", logicWorld, false, j+i*100, checkOverlaps);
                
            }

        }*/

    G4Box* solidDetector = new G4Box("solidDetector", 0.5 * detectorSize, 0.25 * detectorSize, 0.01 * m);
    logicDetector = new G4LogicalVolume(solidDetector, worldMat, "logicDetector");
    G4VPhysicalVolume* physDetector = new G4PVPlacement(0, G4ThreeVector(0 * m , -0.025 * m, 0.19 * m), logicDetector, "physDetector", logicWorld, false, 1, checkOverlaps);

    return physWorld;
}

void PMDetectorConstruction::ConstructSDandField()
{
    PMSensitiveDetector *sensDet = new PMSensitiveDetector("SensitveDetector");
    logicDetector->SetSensitiveDetector(sensDet);
    G4SDManager::GetSDMpointer()->AddNewDetector(sensDet);
}