#ifndef PMSensitiveDetector_h
#define PMSensitiveDetector_h 1

#include "G4VSensitiveDetector.hh"
#include <fstream>
#include <mutex>

class PMSensitiveDetector : public G4VSensitiveDetector
{
public:
    PMSensitiveDetector(G4String name);
    virtual ~PMSensitiveDetector();

    virtual void Initialize(G4HCofThisEvent*);
    virtual G4bool ProcessHits(G4Step*, G4TouchableHistory*);
    virtual void EndOfEvent(G4HCofThisEvent*);

private:
    static std::ofstream outFile;
    static std::mutex fileMutex;

    // Вспомогательные функции для дискретизации
    int GetDiscreteIndex(G4double position, G4double size, int numBins);
    G4double GetDiscretePosition(int index, G4double size, int numBins);
};

extern G4int photon_count;

#endif