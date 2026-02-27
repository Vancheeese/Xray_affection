#include "PMRunAction.hh"
#include "PMSensitiveDetector.hh"
#include "PMDetectorConstruction.hh"
#include "PMPrimaryGenerator.hh"
#include "G4Threading.hh"


PMRunAction::PMRunAction()
{
    
    G4AnalysisManager *analysisManager = G4AnalysisManager::Instance();

}

PMRunAction::~PMRunAction()
{
}

void PMRunAction::BeginOfRunAction(const G4Run *run)
{
    G4AnalysisManager* man = G4AnalysisManager::Instance();



    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->SetNtupleMerging(true);
    man->OpenFile("output.root");

    man->CreateNtuple("Hits", "Hits");
    man->CreateNtupleIColumn("fEvent");
    man->CreateNtupleDColumn("fX");
    man->CreateNtupleDColumn("fY");
    man->CreateNtupleDColumn("fZ");
    //man->CreateNtupleDColumn("straight");
    man->FinishNtuple(0);


  /*  G4AnalysisManager *analysisManager = G4AnalysisManager::Instance();

    G4int runID = run->GetRunID();

    std::stringstream strRunID;
    strRunID << runID;

    analysisManager->OpenFile("output" + strRunID.str() + ".root");*/
}

void PMRunAction::EndOfRunAction(const G4Run *run)
{
    {
        // G4cout << "Pass photons: " << photon_count << G4endl;
         //"Material: " << leadMat;
        G4cout << "Pass photons: " << photon_count << G4endl;
        G4cout << "Energy: " << energy << " keV" << G4endl;
        G4cout << "Material: " << material << G4endl;
        G4cout << "Thickness: " << leadThickness << " mm" << G4endl;
#ifdef G4MULTITHREADED
        static G4Mutex stuffMutex = G4MUTEX_INITIALIZER;
        G4AutoLock al(&stuffMutex);
#endif
        if (G4Threading::IsMasterThread()) {
            static std::ofstream stuff("stuff.csv");
            static bool first = true;
            if (first) {
                first = false;
                stuff << "Material: " << material << std::endl;
                stuff << "Thickness: " << leadThickness << " mm" << std::endl;
            }
            stuff << "Pass photons: " << photon_count << std::endl;
            stuff << "Energy: " << energy*1000 << " keV" << std::endl;

            stuff.flush();
        }

    }
}