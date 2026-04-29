#include "PMPrimaryGenerator.hh"
#include "G4SystemOfUnits.hh"
#include "G4Event.hh"
#include "G4ParticleTable.hh"
#include "Randomize.hh"
#include "G4RunManager.hh"
#include "G4AutoLock.hh"
#include <iostream>

std::atomic<G4int> PMPrimaryGenerator::fGlobalPixelX(0);
std::atomic<G4int> PMPrimaryGenerator::fGlobalPixelY(0);
std::atomic<G4int> PMPrimaryGenerator::fParticlesEmittedInCurrentPixel(0);
const G4int PMPrimaryGenerator::fParticlesPerPixel = 500;  // N частиц на точку
const G4int PMPrimaryGenerator::fGridSize = 100;
std::atomic<G4bool> PMPrimaryGenerator::fIsFinished(false);

G4double energy = 0.;
G4Mutex pixelMutex;

PMPrimaryGenerator::PMPrimaryGenerator()
{
    fParticleGun = new G4ParticleGun(1);

    // Particle type
    G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
    G4ParticleDefinition* particle = particleTable->FindParticle("gamma");

    // Начальная настройка (временная)
    G4ThreeVector pos(0., 0., 0.);
    G4ThreeVector mom(0., 0., 1.);

    fParticleGun->SetParticlePosition(pos);
    fParticleGun->SetParticleMomentumDirection(mom);
    fParticleGun->SetParticleEnergy(40. * keV);
    fParticleGun->SetParticleDefinition(particle);
}

PMPrimaryGenerator::~PMPrimaryGenerator()
{
    delete fParticleGun;
}

G4int PMPrimaryGenerator::GetCurrentPixelX()
{
    return fGlobalPixelX.load();
}

G4int PMPrimaryGenerator::GetCurrentPixelY()
{
    return fGlobalPixelY.load();
}

void PMPrimaryGenerator::SetSourcePosition(G4double x, G4double y)
{
    G4ThreeVector pos(x, y, 0.);
    fParticleGun->SetParticlePosition(pos);
}

// Функция для получения центра бина детектора по индексу
// Совпадает с формулой из SensitiveDetector
G4double GetDetectorBinCenter(int index, G4double size, int numBins)
{
    G4double step = (2.0 * size) / numBins;  // step = 10 см / 25 = 0.4 см
    G4double position = -size + (index + 0.5) * step;
    return position;
}

void PMPrimaryGenerator::GeneratePrimaries(G4Event* anEvent)
{
    // Быстрая проверка флага
    if (fIsFinished.load()) {
        return;
    }

    G4int currentX, currentY;
    G4bool shouldGenerate = false;
    G4bool needAbort = false;

    // Критическая секция для обновления позиции
    {
        G4AutoLock lock(&pixelMutex);

        if (fIsFinished.load()) return;

        currentX = fGlobalPixelX.load();
        currentY = fGlobalPixelY.load();
        G4int particlesInPixel = fParticlesEmittedInCurrentPixel.load();

        if (particlesInPixel >= fParticlesPerPixel) {
            // Переходим к следующему пикселю
            fParticlesEmittedInCurrentPixel = 0;
            currentX++;

            if (currentX >= fGridSize) {
                currentX = 0;
                currentY++;

                if (currentY >= fGridSize) {
                    fIsFinished = true;
                    G4cout << "Thread " << G4Threading::G4GetThreadId()
                        << ": All pixels processed." << G4endl;
                    needAbort = true;
                    lock.unlock();
                    // Запрашиваем остановку
                    G4RunManager::GetRunManager()->AbortRun();
                    return;
                }
            }

            fGlobalPixelX = currentX;
            fGlobalPixelY = currentY;
        }

        // Увеличиваем счетчик
        fParticlesEmittedInCurrentPixel++;
        shouldGenerate = true;
    }

    // Генерируем событие только если не завершили
    if (shouldGenerate && !fIsFinished.load()) {
        // Используем ТУ ЖЕ САМУЮ формулу, что и в SensitiveDetector
        const G4double range = 5.0 * cm;   // от -5 см до +5 см
        const G4int numBins = fGridSize;           // 25 бинов

        // Вычисляем центр бина детектора
        G4double x = GetDetectorBinCenter(currentX, range, numBins);
        G4double y = GetDetectorBinCenter(currentY, range, numBins);

        SetSourcePosition(x, y);
        energy = fParticleGun->GetParticleEnergy();

        // Генерируем вершину
        fParticleGun->GeneratePrimaryVertex(anEvent);

        // Логирование
        static G4ThreadLocal G4int lastPixelX = -1;
        static G4ThreadLocal G4int lastPixelY = -1;

        if (lastPixelX != currentX || lastPixelY != currentY) {
            lastPixelX = currentX;
            lastPixelY = currentY;
            G4cout << "Thread " << G4Threading::G4GetThreadId()
                << " processing pixel [" << currentX << "," << currentY
                << "] at (" << x / cm << " cm, " << y / cm << " cm)"
                << G4endl;
        }
    }
}