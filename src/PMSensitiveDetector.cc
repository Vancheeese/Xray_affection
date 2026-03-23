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
    static std::ofstream stuff1("stuff1.csv");
    static std::mutex file_mutex;  // ћьютекс дл€ синхронизации
  
        G4Track* track = aStep->GetTrack();

        G4StepPoint* preStepPoint = aStep->GetPreStepPoint();
        G4ThreeVector posPhoton = preStepPoint->GetPosition();
        G4double angle;
        G4double compton_energy;
        G4double energy = track->GetKineticEnergy();

        G4double E0 = 100.0;       
        G4double m_e_c2 = 511.0;

        angle = atan(sqrt(posPhoton(0) * posPhoton(0) + posPhoton(1) * posPhoton(1)) / 90);
        compton_energy = E0 / (1 + (E0 / m_e_c2) * (1 - cos(angle)));

        std::stringstream ss;
        if ( energy !=0.1 && energy> compton_energy/1000-0.004 && energy < compton_energy / 1000 + 0.004) {
        ss << "Particle energy: " << energy * 1000 << " keV";
  
        
        // ss << " Position: " << posPhoton(0) << " " << posPhoton(1) << " "<< angle << std::endl;
        //ss << " Angle: " << angle << " Compton: " << compton_energy << std::endl;
        ss << " Angle: " << angle << std::endl;
        }


        {
            std::lock_guard<std::mutex> lock(file_mutex);
            stuff1 << ss.str();
            stuff1.flush();
        }
         
           // track->SetTrackStatus(fStopAndKill);
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