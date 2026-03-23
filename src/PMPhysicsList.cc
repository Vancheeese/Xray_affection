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

void PMPhysicsList::ConstructProcess()
{
    G4VModularPhysicsList::ConstructProcess();

    G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
    G4ParticleTable::G4PTblDicIterator* theParticleIterator = particleTable->GetIterator();

    theParticleIterator->reset();
    while ((*theParticleIterator)())
    {
        G4ParticleDefinition* particle = theParticleIterator->value();
        G4ProcessManager* pmanager = particle->GetProcessManager();
        G4String particleName = particle->GetParticleName();

        if (particleName == "gamma")
        {
            G4ComptonScattering* compt = new G4ComptonScattering();
            compt->SetEmModel(new G4KleinNishinaModel());
            pmanager->AddDiscreteProcess(compt);
            break;  // Только один гамма
        }
    }
}