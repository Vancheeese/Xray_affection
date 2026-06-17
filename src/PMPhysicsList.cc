#include "PMPhysicsList.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4OpticalPhysics.hh"
#include "G4Scintillation.hh"
#include "G4ProcessManager.hh"
#include "G4Gamma.hh"
#include "G4Electron.hh"
#include "G4EmStandardPhysics_option4.hh"

PMPhysicsList::PMPhysicsList()
{
    RegisterPhysics(new G4EmStandardPhysics_option4());
    RegisterPhysics(new G4OpticalPhysics());

}

PMPhysicsList::~PMPhysicsList()
{
}