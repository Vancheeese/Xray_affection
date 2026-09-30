#include "PMRunAction.hh"

PMRunAction::PMRunAction()
{
}

PMRunAction::~PMRunAction()
{
}

void PMRunAction::BeginOfRunAction(const G4Run *run)
{
    auto analysisManager = G4AnalysisManager::Instance();
    analysisManager->SetNtupleMerging(true);
}

void PMRunAction::EndOfRunAction(const G4Run *run)
{
}
