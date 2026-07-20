#include "PMSensitiveDetector.hh"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4OpticalPhoton.hh"
#include "G4SystemOfUnits.hh"
#include <cmath>
#include "G4RunManager.hh"
#include "G4Event.hh"
#include "G4Threading.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleTable.hh"

G4Mutex PMSensitiveDetector::closeMutex = G4MUTEX_INITIALIZER;
std::ofstream PMSensitiveDetector::outFile;

PMSensitiveDetector::PMSensitiveDetector(G4String name)
    : G4VSensitiveDetector(name)
{
    static bool fileOpened = false;
    if (!fileOpened) {
        outFile.open("hits_data.csv");
        if (outFile.is_open()) {
            outFile << "Energy_eV	PosX_um	PosY_um	Type	EventID\n";
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
        G4AutoLock al(&closeMutex);
        if (!fileClosed) {
            outFile.close();
            G4cout << "File hits_data.csv closed" << G4endl;
            fileClosed = true;
        }
    }
}

void PMSensitiveDetector::Initialize(G4HCofThisEvent*)
{
}

G4bool PMSensitiveDetector::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
    G4Track* track = aStep->GetTrack();
    G4ParticleDefinition* particle = track->GetDefinition();
    G4String particleName = particle->GetParticleName();
    G4double energy = track->GetKineticEnergy() / eV;
    G4int eventID = track->GetTrackID();

    G4StepPoint* postStepPoint = aStep->GetPostStepPoint();
    G4ThreeVector hitPos = postStepPoint->GetPosition();

    if (outFile.is_open()) {
        G4AutoLock lock(&closeMutex);
        outFile << energy << "	"
            << hitPos.x() / um << "	"
            << hitPos.y() / um << "	"
            << particleName << "	"
            << eventID
            << "\n";
    }

    track->SetTrackStatus(fStopAndKill);
    return true;
}

void PMSensitiveDetector::EndOfEvent(G4HCofThisEvent*)
{
}