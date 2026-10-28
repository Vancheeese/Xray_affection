#include "PMPrimaryGenerator.hh"
#include "G4SystemOfUnits.hh"
#include "G4Event.hh"
#include "G4ParticleTable.hh"
#include "Randomize.hh"
#include "G4RunManager.hh"
#include "G4AutoLock.hh"
#include "global_parameters.hh"
#include <iostream>
#include <cmath>
#include <algorithm>

std::atomic<G4int>  PMPrimaryGenerator::fGlobalPixelX(0);
std::atomic<G4int>  PMPrimaryGenerator::fGlobalPixelY(0);
std::atomic<G4int>  PMPrimaryGenerator::fParticlesEmittedInCurrentPixel(0);
std::atomic<G4bool> PMPrimaryGenerator::fIsFinished(false);

G4double energy = 0.;
G4Mutex pixelMutex;

// =====================================================================
// Конструктор
// =====================================================================
PMPrimaryGenerator::PMPrimaryGenerator()
{
    fParticleGun = new G4ParticleGun(1);

    G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
    G4ParticleDefinition* particle = particleTable->FindParticle("gamma");

    // Источник рентгена перед золотыми полосками (Z < 0)
    G4double sourceZ = -10.0 * cm;
    G4ThreeVector pos(0., 0., sourceZ);
    G4ThreeVector mom(0., 0., 1.);

    fParticleGun->SetParticlePosition(pos);
    fParticleGun->SetParticleMomentumDirection(mom);
    fParticleGun->SetParticleDefinition(particle);

    // Энергия будет выставляться per-event в GeneratePrimaries().
    // Здесь ставим значение по умолчанию — на случай, если кто-то
    // вызовет GetParticleEnergy() до первого события.
    if (useRealisticSpectrum) {
        fParticleGun->SetParticleEnergy(17.444 * keV); // центр Kα-дублета
        G4cout << "PMPrimaryGenerator: реалистичный спектр Mo-анода "
               << "(Brems + Kα 17.44 + Kβ 19.61 keV)" << G4endl;
    } else {
        fParticleGun->SetParticleEnergy(initialEnergy);
        G4cout << "PMPrimaryGenerator: монохроматический источник, E = "
               << initialEnergy / keV << " keV" << G4endl;
    }
}

PMPrimaryGenerator::~PMPrimaryGenerator()
{
    delete fParticleGun;
}

// =====================================================================
// Вспомогательные методы
// =====================================================================
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
    G4ThreeVector pos(x, y, -10.0 * cm);  // Источник всегда перед золотом
    fParticleGun->SetParticlePosition(pos);
}

G4double GetDetectorBinCenter(int index, G4double size, int numBins)
{
    G4double step = (2.0 * size) / numBins;  // step = 10 ?? / 25 = 0.4 ??
    G4double position = -size + (index + 0.5) * step;
    return position;
}

// =====================================================================
// Выборка энергии из реалистичного спектра Mo-анода
// =====================================================================
//
// Приближённая, но физически разумная модель спектра Mo-анода
// при напряжении ~30 кВ, после ~10 см воздуха между источником и
// образцом (которое срезает Bremsstrahlung ниже ~5 кэВ).
//
// Относительные вклады фотонов (грубая оценка):
//     Bremsstrahlung : ~20 %
//     Kα-дублет      : ~70 %  (Kα1 17.479, Kα2 17.374 → ср. 17.444)
//     Kβ1            : ~10 %  (19.608)
//
// ВАЖНО: для продакшн-расчётов замените эту функцию на выборку
// из таблицы, полученной в SpekPy или из измеренного спектра.
//
G4double PMPrimaryGenerator::SampleMolybdenumEnergy()
{
    const G4double u = G4UniformRand();

    if (u < 0.20) {
        // --- Bremsstrahlung: непрерывный спектр, приближённо 5–30 кэВ
        // с линейно убывающей плотностью (типично для фильтрованного спектра).
        // Обратное преобразование для PDF ∝ (Emax − E):
        //     F(E) = 1 − (Emax − E)^2 / (Emax − Emin)^2
        //     E = Emax − (Emax − Emin) * sqrt(1 − v)
        const G4double Emin = 5.0;   // кэВ
        const G4double Emax = 30.0;  // кэВ
        const G4double v = G4UniformRand();
        const G4double E_keV = Emax - (Emax - Emin) * std::sqrt(1.0 - v);
        return E_keV * keV;
    }
    else if (u < 0.90) {
        // --- Kα-дублет: эффективно гауссова линия около 17.444 кэВ.
        // σ ≈ 0.05 кэВ — типичная естественная ширина + разрешение.
        // Для «чистого» Geant4-моделирования можно уменьшить до 0.005 кэВ.
        const G4double E_keV = 17.444 + G4RandGauss::shoot(0.0, 0.05);
        return std::max(0.1, E_keV) * keV;
    }
    else {
        // --- Kβ1: 19.608 кэВ
        const G4double E_keV = 19.608 + G4RandGauss::shoot(0.0, 0.05);
        return std::max(0.1, E_keV) * keV;
    }
}

// =====================================================================
// Генерация первичных частиц
// =====================================================================
void PMPrimaryGenerator::GeneratePrimaries(G4Event* anEvent)
{
    if (fIsFinished.load()) {
        return;
    }

    G4int currentX, currentY;
    G4bool shouldGenerate = false;
    G4bool needAbort = false;

    {
        G4AutoLock lock(&pixelMutex);

        if (fIsFinished.load()) return;

        currentX = fGlobalPixelX.load();
        currentY = fGlobalPixelY.load();
        G4int particlesInPixel = fParticlesEmittedInCurrentPixel.load();

        if (particlesInPixel >= particlesPerPixel) {
            fParticlesEmittedInCurrentPixel = 0;
            currentX++;

            if (currentX >= gridSize) {
                currentX = 0;
                currentY++;

                if (currentY >= gridSize) {
                    fIsFinished = true;
                    G4cout << "Thread " << G4Threading::G4GetThreadId()
                           << ": All pixels processed." << G4endl;
                    needAbort = true;
                    lock.unlock();
                    G4RunManager::GetRunManager()->AbortRun();
                    return;
                }
            }

            fGlobalPixelX = currentX;
            fGlobalPixelY = currentY;
        }

        fParticlesEmittedInCurrentPixel++;
        shouldGenerate = true;
    }

    if (shouldGenerate && !fIsFinished.load()) {
        // Рассчитываем координаты частиц по размеру области, как и в SensitiveDetector
        const G4double range  = pixelSize * gridSize / 2;
        const G4int    numBins = gridSize;

        // Генерируем частицы по размеру области
        G4double x = GetDetectorBinCenter(currentX, range, numBins);
        G4double y = GetDetectorBinCenter(currentY, range, numBins);

        // Равномерно по площади пикселя, а не строго в его центр: иначе
        // на изображении с шагом 1 мкм появляется детерминированная решётка
        // с периодом pixelSize, которая растёт ∝ N и портит оценку шума/SNR.
        x += (G4UniformRand() - 0.5) * pixelSize;
        y += (G4UniformRand() - 0.5) * pixelSize;

        SetSourcePosition(x, y);

        // ===== ВЫБОР ЭНЕРГИИ =====
        if (useRealisticSpectrum) {
            fParticleGun->SetParticleEnergy(SampleMolybdenumEnergy());
        } else {
            fParticleGun->SetParticleEnergy(initialEnergy);
        }
        energy = fParticleGun->GetParticleEnergy();
        // ===== КОНЕЦ ВЫБОРА ЭНЕРГИИ =====

        // ====== ОТЛАДКА: проверка попадания в золото ======
        static G4int totalEvents = 0;
        static G4int goldHits    = 0;
        totalEvents++;

        G4double leadSize   = pixelSize * gridSize;
        G4double slitPeriod = slitWidth + slitWidth;
        G4int    numSlits   = (G4int)(leadSize / slitPeriod);
        G4double totalWidth = numSlits * slitPeriod;
        G4double startX     = -totalWidth / 2.0 + slitWidth / 2.0;
        bool onGold = false;
        for (G4int i = 0; i < numSlits; ++i) {
            G4double xMin = startX + i * slitPeriod - slitWidth / 2.0;
            G4double xMax = startX + i * slitPeriod + slitWidth / 2.0;
            if (x >= xMin && x <= xMax) {
                onGold = true;
                break;
            }
        }
        if (onGold) goldHits++;

        if (totalEvents % 1000 == 0) {
            G4cout << "[DEBUG] Events: " << totalEvents
                   << ", Gold hits: " << goldHits
                   << ", Fraction: " << (G4double)goldHits / totalEvents
                   << G4endl;
        }
        // ====== КОНЕЦ ОТЛАДКИ ======

        // Генерируем первичную вершину
        fParticleGun->GeneratePrimaryVertex(anEvent);

        // Логирование перехода между пикселями
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