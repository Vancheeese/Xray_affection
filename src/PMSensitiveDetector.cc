#include "PMSensitiveDetector.hh"


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
    G4StepPoint* preStepPoint = aStep->GetPreStepPoint();

    // Проверка aStep на nullptr
    //if (!aStep) {
    //    G4Exception("PMSensitiveDetector::ProcessHits", "Error", FatalException,
    //        "aStep is null");
    //    return false;
    //}

    //// Проверка GetTrack()
    //G4Track* track = aStep->GetTrack();
    //if (!track) {
    //    G4Exception("PMSensitiveDetector::ProcessHits", "Error", FatalException,
    //        "track is null");
    //    return false;
    //}

    //// Проверка GetPreStepPoint()
    //G4StepPoint* preStepPoint = aStep->GetPreStepPoint();
    //if (!preStepPoint) {
    //    G4Exception("PMSensitiveDetector::ProcessHits", "Error", FatalException,
    //        "preStepPoint is null");
    //    return false;
    //}

    //G4StepPoint *postStepPoint = aStep->GetPostStepPoint();

    G4ThreeVector posPhoton = preStepPoint->GetPosition();
    G4cout << "Photon position: " << posPhoton << G4endl;
    

        G4int evt = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();


        G4AnalysisManager* man = G4AnalysisManager::Instance();
        man->FillNtupleIColumn(0, evt);
        man->FillNtupleDColumn(1, posPhoton[0]);
        man->FillNtupleDColumn(2, posPhoton[1]);
        man->FillNtupleDColumn(3, posPhoton[2]);

        //if (posPhoton[0] == 0)
        //{

        //    man->FillNtupleDColumn(4, posPhoton[1]);
        //    //G4cout << "Photon position: " << posPhoton << G4endl;

        //}

        man->AddNtupleRow(0);


        //outFile << "Photon position: " << posPhoton << G4endl;

        //outFile.close();

      


    
    

    const G4VTouchable* touchable = aStep->GetPreStepPoint()->GetTouchable();

    G4int copyNo = touchable->GetCopyNumber();

    //G4cout << "Copy number: " << copyNo << G4endl;

    G4VPhysicalVolume* physVol = touchable->GetVolume();
    G4ThreeVector posDetector = physVol->GetTranslation();

    //G4cout << "Detector position: " << posDetector << G4endl;
    
    return true;
}

void PMSensitiveDetector::EndOfEvent(G4HCofThisEvent *)
{
   // outFile.close();
    //G4cout << "Deposited energy: " << fTotalEnergyDeposited << G4endl;
}