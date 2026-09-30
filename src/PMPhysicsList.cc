#include "PMPhysicsList.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4OpticalPhysics.hh"
#include "G4SystemOfUnits.hh"
#include "G4LossTableManager.hh"
#include "G4ProcessManager.hh"
#include <iostream>

PMPhysicsList::PMPhysicsList()
{
    G4cout << "=== PMPhysicsList: Initializing ===" << G4endl;
    SetVerboseLevel(1);

    G4LossTableManager::Instance();

    RegisterPhysics(new G4EmLivermorePhysics());
    RegisterPhysics(new G4OpticalPhysics());

    G4cout << "=== PMPhysicsList: Done ===" << G4endl;
}

PMPhysicsList::~PMPhysicsList()
{}

void PMPhysicsList::ConstructProcess()
{
    G4cout << "=== PMPhysicsList::ConstructProcess() ===" << G4endl;

    // Стандартные процессы, включая оптические.
    G4VModularPhysicsList::ConstructProcess();

    G4cout << "=== PMPhysicsList::ConstructProcess() Done ===" << G4endl;
}