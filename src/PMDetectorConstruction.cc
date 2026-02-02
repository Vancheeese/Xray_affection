#include "PMDetectorConstruction.hh"
#include "G4PhysicalConstants.hh"


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
    G4Material *leadMat = nist->FindOrBuildMaterial("G4_Al");       //G4_Al->G4_Cu      для замены алюминия на медь
    G4Material *detMat = nist->FindOrBuildMaterial("G4_SODIUM_IODIDE");


    G4double xWorld = 1. * m;
    G4double yWorld = 1. * m;
    G4double zWorld = 1. * m;

    G4Box *solidWorld = new G4Box("solidWorld", 0.5 * xWorld, 0.5 * yWorld, 0.5 * zWorld);
    G4LogicalVolume *logicWorld = new G4LogicalVolume(solidWorld, worldMat, "logicalWorld");
    G4VPhysicalVolume *physWorld = new G4PVPlacement(0, G4ThreeVector(0., 0., 0.), logicWorld, "physWorld", 0, false, 0);

    G4double leadThickness = 100. * mm;             //изменение толщины пластины (текущая толщина 100 мкм)
    G4double leadSize = 10. * cm;
    G4Box *solidLead = new G4Box("solidLead", 0.5 * leadSize, 0.5 * leadSize, 0.001 * leadThickness);
    G4LogicalVolume *logicLead = new G4LogicalVolume(solidLead, leadMat, "logicLead");
    G4VPhysicalVolume *physLead = new G4PVPlacement(0, G4ThreeVector(0., 0., 10. * cm), logicLead, "physLead", logicWorld, false, checkOverlaps);

    G4VisAttributes *leadVisAtt = new G4VisAttributes(G4Color(1.0, 0.0, 0.0, 0.5));
    leadVisAtt->SetForceSolid(true);
    logicLead->SetVisAttributes(leadVisAtt);

    G4double detectorSize = 10.0 * cm;

    G4Box *solidDetector = new G4Box("solidDetector", 0.005*m, 0.005*m, 0.001*m);
    logicDetector = new G4LogicalVolume(solidDetector, worldMat, "logicDetector");
        for (G4int i=0; i<50; i++)
        {
            for (G4int j=0; j<50; j++)
            {
                G4VPhysicalVolume *physDetector = new G4PVPlacement(0, G4ThreeVector(-0.2525*m+(i+0.5)*m/100, -0.2525*m+(j+0.5)*m/100 , 0.19 *m), logicDetector, "physDetector", logicWorld, false, j+i*100, checkOverlaps);
                
            }

        }


    return physWorld;
}

void PMDetectorConstruction::ConstructSDandField()
{
    PMSensitiveDetector *sensDet = new PMSensitiveDetector("SensitveDetector");
    logicDetector->SetSensitiveDetector(sensDet);
    G4SDManager::GetSDMpointer()->AddNewDetector(sensDet);
}