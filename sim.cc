#include <iostream>
#include <cstdlib> // ��� std::atof

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

#ifdef G4MULTITHREADED
    G4MTRunManager* runManager = new G4MTRunManager;
    runManager->SetNumberOfThreads(12);
#else
    G4RunManager* runManager = new G4RunManager;
#endif

    // Physics list
    runManager->SetUserInitialization(new PMPhysicsList());

    // --- �������� � ������������ ������� ������� ---
    PMDetectorConstruction* detector = new PMDetectorConstruction();
    runManager->SetUserInitialization(detector);

    // Action initialization
    runManager->SetUserInitialization(new PMActionInitialization());

    // �������������� runManager (�����: ����� ������� �������)
    runManager->Initialize();

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
        UImanager->ApplyCommand(command + fileName);
    }

    delete visManager;
    delete runManager;
    return 0;
}