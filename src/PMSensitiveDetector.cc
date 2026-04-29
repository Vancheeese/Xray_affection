#include "PMSensitiveDetector.hh"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4SystemOfUnits.hh"
#include <cmath>

std::ofstream PMSensitiveDetector::outFile;
std::mutex PMSensitiveDetector::fileMutex;

PMSensitiveDetector::PMSensitiveDetector(G4String name)
    : G4VSensitiveDetector(name)
{
    // Открываем файл только один раз
    static bool fileOpened = false;
    if (!fileOpened) {
        outFile.open("hits_data.csv");
        if (outFile.is_open()) {
            outFile << "Energy_keV\tPosX_cm\tPosY_cm\n";
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
    // Закрываем файл при разрушении последнего экземпляра
    static bool fileClosed = false;
    if (!fileClosed && outFile.is_open()) {
        outFile.close();
        G4cout << "File hits_data.csv closed" << G4endl;
        fileClosed = true;
    }
}

void PMSensitiveDetector::Initialize(G4HCofThisEvent*)
{
    // Ничего не делаем
}

// Функция для преобразования непрерывной позиции в дискретный индекс
// range: от -size до +size
// numBins: количество дискретных позиций в диапазоне [-size, size]
int PMSensitiveDetector::GetDiscreteIndex(G4double position, G4double size, int numBins)
{
    // Проверяем границы
    if (position <= -size) return 0;
    if (position >= size) return numBins - 1;

    // Преобразуем в индекс [0, numBins-1]
    G4double normalized = (position + size) / (2.0 * size); // от 0 до 1
    int index = static_cast<int>(normalized * numBins);

    // Защита от выхода за границы
    if (index < 0) index = 0;
    if (index >= numBins) index = numBins - 1;

    return index;
}

// Функция для получения значения дискретной позиции по индексу
G4double PMSensitiveDetector::GetDiscretePosition(int index, G4double size, int numBins)
{
    G4double step = (2.0 * size) / numBins;
    G4double position = -size + (index + 0.5) * step;
    return position;
}

G4bool PMSensitiveDetector::ProcessHits(G4Step* aStep, G4TouchableHistory*)
{
    G4Track* track = aStep->GetTrack();
    G4StepPoint* preStepPoint = aStep->GetPreStepPoint();

    // Получаем энергию частицы
    G4double energy = track->GetKineticEnergy();

    // Получаем позицию хита в детекторе
    G4ThreeVector hitPos = preStepPoint->GetPosition();

    // Параметры дискретизации: от -5 см до 5 см (общий диапазон 10 см)
    const G4double range = 5.0 * cm;      // -5 см до +5 см
    const int numBins = 100;                // 25 позиций в каждом направлении → всего 625 комбинаций

    // Получаем дискретные индексы для X и Y координат
    int binX = GetDiscreteIndex(hitPos.x(), range, numBins);
    int binY = GetDiscreteIndex(hitPos.y(), range, numBins);

    // Получаем фактические дискретные позиции (центры бинов)
    G4double discreteX = GetDiscretePosition(binX, range, numBins);
    G4double discreteY = GetDiscretePosition(binY, range, numBins);

    // Записываем в файл: энергию, индексы бинов, дискретные позиции
    if (outFile.is_open()) {
        std::lock_guard<std::mutex> lock(fileMutex);
        outFile << energy / keV << "\t"
        //    << binX << "\t"
        //    << binY << "\t"
            << discreteX / cm << "\t"
            << discreteY / cm << std::endl;
    }

    return true;
}

void PMSensitiveDetector::EndOfEvent(G4HCofThisEvent*)
{
    // Ничего не делаем
}