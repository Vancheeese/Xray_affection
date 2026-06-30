#include "PMPhysicsList.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4OpticalPhysics.hh"

PMPhysicsList::PMPhysicsList()
{
    // G4EmLivermorePhysics — точное моделирование взаимодействия рентгена с веществом
    RegisterPhysics(new G4EmLivermorePhysics());
    
    // G4OpticalPhysics — для моделирования сцинтилляции и оптических фотонов
    RegisterPhysics(new G4OpticalPhysics());
}

PMPhysicsList::~PMPhysicsList()
{
}