#include "PMPhysicsList.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4VModularPhysicsList.hh"
#include "G4OpticalPhysics.hh"


PMPhysicsList::PMPhysicsList()
{
        // Низкоэнергетическая ЭМ физика (от ~250 eV до 100 GeV)
        RegisterPhysics(new G4EmLivermorePhysics());

    //RegisterPhysics(new G4EmStandardPhysics());

        // Опционально: добавить оптическую физику
         RegisterPhysics(new G4OpticalPhysics());
    }



PMPhysicsList::~PMPhysicsList()
{
}