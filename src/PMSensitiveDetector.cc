#include "PMSensitiveDetector.hh"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4OpticalPhoton.hh"
#include "G4SystemOfUnits.hh"
#include <cmath>
#include "G4RunManager.hh"
#include "G4Event.hh"

std::ofstream PMSensitiveDetector::outFile;
std::mutex PMSensitiveDetector::fileMutex;

PMSensitiveDetector::PMSensitiveDetector(G4String name)
    : G4VSensitiveDetector(name)
{
    static bool fileOpened = false;
    if (!fileOpened) {
        outFile.open("hits_data.csv");
        if (outFile.is_open()) {
            outFile << "Energy_eV\tPosX_cm\tPosY_cm\tType\tEventID\n";
            G4cout << "File hits_data.csv opened successfully" << G4endl;
        }
        else {
            G4cout << "ERROR: Cannot open hits_data.csv" << G4endl;
        }
        fileOpened = true;
    }
}

PMSensitiveDetector::~PMSensitiveDetector()
{
    static bool fileClosed = false;
    if (!fileClosed && outFile.is_open()) {
        outFile.close();
        G4cout << "File hits_data.csv closed" << G4endl;
        fileClosed = true;
    }
}

void PMSensitiveDetector::Initialize(G4HCofThisEvent*)
{
    // Обнуляем счетчик фотонов для нового события
    eventPhotonCount = 0;
}

G4bool PMSensitiveDetector::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
    G4Track* track = aStep->GetTrack();
    G4ParticleDefinition* particle = track->GetDefinition();

    // Регистрируем ВСЕ фотоны, попавшие в детектор
    if (particle == G4OpticalPhoton::Definition()) {
        eventPhotonCount++;

        // Записываем информацию
        G4StepPoint* postStepPoint = aStep->GetPostStepPoint();
        G4ThreeVector hitPos = postStepPoint->GetPosition();

        if (outFile.is_open()) {
            std::lock_guard<std::mutex> lock(fileMutex);
            outFile << track->GetKineticEnergy() / eV << "\t"
                << hitPos.x() / cm << "\t"
                << hitPos.y() / cm << "\t"
                << "optical_photon\t"
                << G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID() << "\n";
        }

        // ПРИНУДИТЕЛЬНО поглощаем фотон (имитация 100% квантовой эффективности)
        track->SetTrackStatus(fStopAndKill);
        return true;
    }

    return false;
}

void PMSensitiveDetector::EndOfEvent(G4HCofThisEvent*)
{
    // Ничего не делаем - PHOTON_COUNT не используется в img.py
}