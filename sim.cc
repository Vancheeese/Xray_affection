#include <iostream>
#include <cstdlib> // for std::atof

#include "G4RunManager.hh"
#include "G4MTRunManager.hh"
#include "G4UImanager.hh"
#include "G4VisManager.hh"
#include "G4VisExecutive.hh"
#include "G4UIExecutive.hh"

#include "PMPhysicsList.hh"
#include "PMDetectorConstruction.hh"
#include "PMActionInitialization.hh"

int main(int argc, char** argv)
{
    G4UIExecutive* ui = nullptr;

    // --- Проверка: однопоточный или многопоточный ---
#ifdef G4MULTITHREADED
    G4cout << "=== MULTI-THREADED MODE ===" << G4endl;
    G4MTRunManager* runManager = new G4MTRunManager;
    runManager->SetNumberOfThreads(12);
#else
    G4cout << "=== SINGLE-THREADED MODE ===" << G4endl;
    G4RunManager* runManager = new G4RunManager;
#endif

    // 1. Physics list (первым, для правильной инициализации)
    G4cout << "Setting physics list..." << G4endl;
    runManager->SetUserInitialization(new PMPhysicsList());

    // 2. Detector construction
    G4cout << "Setting detector construction..." << G4endl;
    PMDetectorConstruction* detector = new PMDetectorConstruction();
    runManager->SetUserInitialization(detector);

    // 3. Action initialization
    G4cout << "Setting action initialization..." << G4endl;
    runManager->SetUserInitialization(new PMActionInitialization());

    // Initialize run manager (должен быть после всех SetUserInitialization)
    G4cout << "Initializing run manager..." << G4endl;
    runManager->Initialize();
    G4cout << "Run manager initialized." << G4endl;

    if (argc == 1) {
        ui = new G4UIExecutive(argc, argv);
    }

    G4VisManager* visManager = new G4VisExecutive();
    visManager->Initialize();

    G4UImanager* UImanager = G4UImanager::GetUIpointer();

    if (ui) {
        UImanager->ApplyCommand("/control/execute vis.mac");
        ui->SessionStart();
    }
    else {
        G4String command = "/control/execute ";
        G4String fileName = argv[1];
        G4cout << "Executing macro: " << fileName << G4endl;
        UImanager->ApplyCommand(command + fileName);
    }

    delete visManager;
    delete runManager;
    return 0;
}