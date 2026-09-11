#include "PMPhysicsList.hh"
#include "G4EmLivermorePhysics.hh"
#include "G4OpticalPhysics.hh"
#include "G4SystemOfUnits.hh"
#include "G4LossTableManager.hh"
#include "G4ProcessManager.hh"
#include "G4Gamma.hh"
#include "G4PhotoElectricEffect.hh"
#include "G4ComptonScattering.hh"
#include "G4GammaConversion.hh"
#include "G4RayleighScattering.hh"
#include <iostream>

PMPhysicsList::PMPhysicsList()
{
    G4cout << "=== PMPhysicsList: Initializing ===" << G4endl;
    SetVerboseLevel(1);

    // Подключаем таблицу потерь энергии
    G4LossTableManager::Instance();

    // Регистрируем физику
    G4cout << "Registering G4EmLivermorePhysics..." << G4endl;
    RegisterPhysics(new G4EmLivermorePhysics());

    G4cout << "Registering G4OpticalPhysics..." << G4endl;
    RegisterPhysics(new G4OpticalPhysics());

    G4cout << "=== PMPhysicsList: Done ===" << G4endl;
}

PMPhysicsList::~PMPhysicsList()
{
}

// Явная регистрация процессов для гамма-частиц
void PMPhysicsList::ConstructProcess()
{
      G4cout << "=== PMPhysicsList::ConstructProcess() ===" << G4endl;
    // Вызываем базовый метод, который запускает G4EmLivermorePhysics и G4OpticalPhysics
    G4VModularPhysicsList::ConstructProcess();
    G4cout << "=== PMPhysicsList::ConstructProcess() Done ===" << G4endl;
}