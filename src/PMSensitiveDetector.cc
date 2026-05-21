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

// Определение статических констант (только здесь, в .cc файле)
const G4ThreeVector PMSensitiveDetector::fInitialDirection(0, 0, 1);
const G4double PMSensitiveDetector::fInitialEnergy = 40.0 * keV;
const G4double PMSensitiveDetector::fEnergyTolerance = 0.05;
const G4double PMSensitiveDetector::fAngleTolerance = 0.01 * deg;

// Определение глобальной переменной (если нужна)
G4int photon_count = 0;

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

int PMSensitiveDetector::GetDiscreteIndex(G4double position, G4double size, int numBins)
{
    if (position <= -size) return 0;
    if (position >= size) return numBins - 1;

    G4double normalized = (position + size) / (2.0 * size);
    int index = static_cast<int>(normalized * numBins);

    if (index < 0) index = 0;
    if (index >= numBins) index = numBins - 1;

    return index;
}

G4double PMSensitiveDetector::GetDiscretePosition(int index, G4double size, int numBins)
{
    G4double step = (2.0 * size) / numBins;
    G4double position = -size + (index + 0.5) * step;
    return position;
}

G4bool PMSensitiveDetector::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
    G4Track* track = aStep->GetTrack();
    G4ParticleDefinition* particle = track->GetDefinition();

    // Проверяем, является ли частица оптическим фотоном
    if (particle == G4OpticalPhoton::Definition()) {
        // Это оптический фотон - регистрируем его
        eventPhotonCount++;
        photon_count++;  // глобальный счетчик

        // Получаем позицию фотона
        G4StepPoint* postStepPoint = aStep->GetPostStepPoint();
        G4ThreeVector hitPos = postStepPoint->GetPosition();

        // Для отладки - выводим информацию о первых фотонах
      /*  if (eventPhotonCount <= 10) {
            G4cout << "Optical photon " << eventPhotonCount
                << " detected at (" << hitPos.x() / cm << ", "
                << hitPos.y() / cm << ", " << hitPos.z() / cm << ") cm"
                << " Energy: " << track->GetKineticEnergy() / eV << " eV" << G4endl;
        }*/

        // Записываем информацию о фотоне в файл
        if (outFile.is_open()) {
            std::lock_guard<std::mutex> lock(fileMutex);
            outFile << track->GetKineticEnergy() / eV << "\t"
                << hitPos.x() / cm << "\t"
                << hitPos.y() / cm << "\t"
                << hitPos.z() / cm << "\t"
                << "optical_photon\t"
                << G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID() << std::endl;
        }

        // Удаляем фотон после регистрации (он поглотился)
        track->SetTrackStatus(fStopAndKill);

        return true;
    }

    // Не оптический фотон - обрабатываем как раньше (гамма, электроны и т.д.)
    G4double currentEnergy = track->GetKineticEnergy();
    G4StepPoint* preStepPoint = aStep->GetPreStepPoint();
    G4ThreeVector currentDir = preStepPoint->GetMomentumDirection();

    // Вычисляем угол между текущим направлением и осью Z
    G4double angleRad = currentDir.angle(fInitialDirection);

    G4String hitType;
    G4double energyRatio = currentEnergy / fInitialEnergy;

    // Критерий: если угол меньше порога И энергия изменилась не более чем на tolerance
    if (angleRad < fAngleTolerance && std::abs(energyRatio - 1.0) < fEnergyTolerance)
        hitType = "pass-through";
    else
        hitType = "scattered";

    // Получаем позицию хита
    G4ThreeVector hitPos = preStepPoint->GetPosition();

    // Параметры дискретизации: от -5 см до 5 см
    const G4double range = 5.0/100 * cm;
    const int numBins = 100;

    int binX = GetDiscreteIndex(hitPos.x(), range, numBins);
    int binY = GetDiscreteIndex(hitPos.y(), range, numBins);
    G4double discreteX = GetDiscretePosition(binX, range, numBins);
    G4double discreteY = GetDiscretePosition(binY, range, numBins);

    // Записываем в файл: энергию, позиции, тип и событие
    if (outFile.is_open()) {
        std::lock_guard<std::mutex> lock(fileMutex);
        outFile << currentEnergy / keV << "\t"
            << discreteX / cm << "\t"
            << discreteY / cm << "\t"
            << hitType << "\t"
            << G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID() << std::endl;
    }

    return true;
}

void PMSensitiveDetector::EndOfEvent(G4HCofThisEvent*)
{

    // В конце события выводим количество зарегистрированных фотонов
    if (eventPhotonCount > 0) {
        /* G4cout << "Event ended. Total optical photons detected: " << eventPhotonCount << G4endl;*/

         // Опционально: записать итог в файл
        if (outFile.is_open()) {
            std::lock_guard<std::mutex> lock(fileMutex);
            outFile << "0\t0\t0\tPHOTON_COUNT\t" << eventPhotonCount << std::endl;
        }
    }
}