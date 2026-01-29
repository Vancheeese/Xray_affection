#include "PMRunAction.hh"

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
    G4AnalysisManager* man = G4AnalysisManager::Instance();

    man->Write();
    man->CloseFile();


  /*  G4AnalysisManager *analysisManager = G4AnalysisManager::Instance();

    analysisManager->Write();

    analysisManager->CloseFile();

    G4int runID = run->GetRunID();

    G4cout << "Finishing run " << runID << G4endl;*/
}