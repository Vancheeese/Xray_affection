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

    // Вызываем базовый метод (зарегистрирует физику из RegisterPhysics)
    G4VModularPhysicsList::ConstructProcess();

    // Дополнительно явно добавляем процессы для гамма
    G4ParticleDefinition* gamma = G4Gamma::Gamma();
    if (gamma) {
        G4ProcessManager* pManager = gamma->GetProcessManager();
        if (pManager) {
            G4cout << "Adding gamma processes explicitly..." << G4endl;

            // Фотоэффект
            G4VProcess* photoElectric = new G4PhotoElectricEffect();
            pManager->AddProcess(photoElectric, -1, -1, 1);
            G4cout << "  Added G4PhotoElectricEffect" << G4endl;

            // Комптон-рассеяние
            G4VProcess* compton = new G4ComptonScattering();
            pManager->AddProcess(compton, -1, -1, 2);
            G4cout << "  Added G4ComptonScattering" << G4endl;

            // Парная генерация
            G4VProcess* pairProd = new G4GammaConversion();
            pManager->AddProcess(pairProd, -1, -1, 3);
            G4cout << "  Added G4GammaConversion" << G4endl;

            // Рэлеевское рассеяние
            G4VProcess* rayleigh = new G4RayleighScattering();
            pManager->AddProcess(rayleigh, -1, -1, 0);
            G4cout << "  Added G4RayleighScattering" << G4endl;

            // Показываем список всех процессов
            G4cout << "Total gamma processes: " << pManager->GetProcessList()->size() << G4endl;
        }
    }

    G4cout << "=== PMPhysicsList::ConstructProcess() Done ===" << G4endl;
}