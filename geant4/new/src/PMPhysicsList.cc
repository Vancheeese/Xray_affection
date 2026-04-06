#include "PMPhysicsList.hh"
#include "G4ComptonScattering.hh"
#include "G4KleinNishinaModel.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"  // ← ЭТОТ HEADER РЕШАЕТ ПРОБЛЕМУ
#include "G4VModularPhysicsList.hh"
#include "G4SystemOfUnits.hh"
#include "G4ProcessManager.hh"
#include "G4EmStandardPhysics.hh" 

PMPhysicsList::PMPhysicsList() : G4VModularPhysicsList()
{
    defaultCutValue = 1.0 * um;
    SetVerboseLevel(1);

    RegisterPhysics(new G4EmStandardPhysics());
}

PMPhysicsList::~PMPhysicsList()
{
}