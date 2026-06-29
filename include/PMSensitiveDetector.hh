#ifndef PMSensitiveDetector_h
#define PMSensitiveDetector_h 1

#include "G4VSensitiveDetector.hh"
#include "G4ThreeVector.hh"
#include <fstream>
#include <mutex>
#include "G4Types.hh"

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
    static G4Mutex closeMutex;

    // Вспомогательные функции для дискретизации
    int GetDiscreteIndex(G4double position, G4double size, int numBins);
    G4double GetDiscretePosition(int index, G4double size, int numBins);

    // Статические константы (только объявление)
    static const G4ThreeVector fInitialDirection;
    static const G4double fInitialEnergy;
    static const G4double fEnergyTolerance;
    static const G4double fAngleTolerance;

    // Счетчик фотонов
    G4int eventPhotonCount = 0;
};

// Внешняя переменная (если нужна)
extern G4int photon_count;

#endif