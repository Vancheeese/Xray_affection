#ifndef PMPRIMARYGENERATOR_HH
#define PMPRIMARYGENERATOR_HH

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4ParticleDefinition.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4SystemOfUnits.hh"
#include "globals.hh"
#include "G4Threading.hh"
#include <atomic>

class PMPrimaryGenerator : public G4VUserPrimaryGeneratorAction
{
public:
    PMPrimaryGenerator();
    ~PMPrimaryGenerator();

    virtual void GeneratePrimaries(G4Event *);

    void SetSourcePosition(G4double x, G4double y);

private:
    G4ParticleGun *fParticleGun;
    
    // Используем атомарные переменные для синхронизации потоков
    static std::atomic<G4int> fGlobalPixelX;
    static std::atomic<G4int> fGlobalPixelY;
    static std::atomic<G4int> fParticlesEmittedInCurrentPixel;
    static const G4int fParticlesPerPixel;
    static const G4int fGridSize;
    static std::atomic<G4bool> fIsFinished;
    
    G4int GetCurrentPixelX();
    G4int GetCurrentPixelY();
};

extern G4double energy;

#endif