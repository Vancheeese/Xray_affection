#include "PMSensitiveDetector.hh"

G4int photon_count = 0;

PMSensitiveDetector::PMSensitiveDetector(G4String name) : G4VSensitiveDetector(name)
{
    //outFile.open("Position.txt");

}

PMSensitiveDetector::~PMSensitiveDetector()
{
    
}

void PMSensitiveDetector::Initialize(G4HCofThisEvent *)
{
    G4int fEventCounter=0;
    fTotalEnergyDeposited = 0.;
    
    
}


G4bool PMSensitiveDetector::ProcessHits(G4Step *aStep, G4TouchableHistory *ROhist)
{
        G4Track* track = aStep->GetTrack();
        if (track->GetKineticEnergy() > 1 * keV && track->GetMomentumDirection().z() > 0.999) {  // Ёнерги€ > порога
            photon_count++;  // √лобальный счЄтчик или в HitsCollection
            track->SetTrackStatus(fStopAndKill);  // ќпционально: поглотить
        }
        return true;
}

void PMSensitiveDetector::EndOfEvent(G4HCofThisEvent *)
{
   // outFile.close();
    //G4cout << "Deposited energy: " << fTotalEnergyDeposited << G4endl;
}