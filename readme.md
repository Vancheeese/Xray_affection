# Xray Affection — Geant4 Simulation

Моделирование взаимодействия рентгеновского излучения с металлическими полосками и регистрацией через сцинтилляцию.

---

## 📁 Структура проекта

```
project/
├── CMakeLists.txt
├── sim.cc                    # Точка входа (main)
├── src/
│   ├── global_parameters.cc  # ⚙️ Глобальные параметры (МЕНЯТЬ ЗДЕСЬ)
│   ├── global_parameters.hh  # Объявления параметров
│   ├── PMDetectorConstruction.cc
│   ├── PMPrimaryGenerator.cc
│   ├── PMPhysicsList.cc
│   └── ...
├── include/
│   └── ...
├── macros/
│   └── one.mac               # Генерируется через generate_mac.py
└── build/
    ├── generate_mac.py        # 🛠 Генератор one.mac
    ├── run_batch_thickness.sh # 🚀 Пакетный запуск
    ├── build_xray_scintillation.py  # 📊 Постобработка (изображения)
    ├── snr_analysis.py        # 📈 Анализ SNR
    └── oimg.py                # 🖼 Простая визуализация
```

---

## 🛠 Генерация mac-файла: `generate_mac.py`

**Что делает:**
Читает `global_parameters.cc` и автоматически создаёт `one.mac` с правильным количеством событий.

**Формула:**
```
total_events = gridSize × gridSize × particlesPerPixel
```

**Запуск:**
```bash
cd build
python3 generate_mac.py
```

**Результат:**
Создаётся файл `build/one.mac`:
```
/run/initialize

# Автоматически сгенерировано: gridSize=100, particlesPerPixel=10
# Общее количество событий = 100² × 10 = 100,000
/run/beamOn 100000
```

**Когда использовать:**
- После изменения `gridSize` или `particlesPerPixel` в `global_parameters.cc`
- Перед каждым запуском `./sim one.mac`

---

## 🚀 Пакетный запуск: `run_batch_thickness.sh`

**Что делает:**
Запускает симуляцию для нескольких толщин сцинтиллятора автоматически.

**Запуск:**
```bash
cd build
bash run_batch_thickness.sh
```

**Как меняются толщины:**

В файле `run_batch_thickness.sh` найдите строку:
```bash
THICKNESSES=(20 100 300)
```

Замените на нужные значения (в мкм):
```bash
THICKNESSES=(10 20 30 50 100 200 500)
```

**Что происходит при запуске:**
1. Для каждой толщины:
   - Меняется `fCsIThickness` в `include/PMDetectorConstruction.hh`
   - Пересобирается проект (`make`)
   - Запускается `./sim one.mac`
   - Запускается `python3 build_xray_scintillation.py`
   - Запускается `python3 snr_analysis.py`
2. Результаты сохраняются в `build/results/{thickness}um/`

**Структура результатов:**
```
build/results/
├── 20um/
│   ├── hits_data.csv
│   ├── xray_scint_full.png
│   ├── xray_scint_attenuation.png
│   ├── snr_histogram.png
│   └── params.txt
├── 100um/
│   └── ...
└── 300um/
    └── ...
```

---

## 🎯 Единичный запуск

**1. Изменить толщину сцинтиллятора:**

Откройте `include/PMDetectorConstruction.hh`:
```cpp
G4double fCsIThickness = 50 * um;  // ← МЕНЯТЬ ЗДЕСЬ (50 мкм)
```

**2. Сгенерировать mac-файл:**
```bash
cd build
python3 generate_mac.py
```

**3. Запустить симуляцию:**
```bash
./sim one.mac
```

**4. Постобработка:**
```bash
python3 build_xray_scintillation.py   # Полные изображения
python3 snr_analysis.py               # SNR анализ
```

---

## ⚙️ Глобальные параметры: `global_parameters.cc`

Файл: `src/global_parameters.cc`

### Доступные параметры:

```cpp
// 1. Размер пикселя детектора (мкм)
G4double pixelSize = 3.5 * um;

// 2. Количество пикселей по одной оси (сетка gridSize × gridSize)
G4int gridSize = 100;

// 3. Ширина золотых полосок и зазоров (мкм)
G4double slitWidth = 25. * um;

// 4. Частиц на один пиксель
G4int particlesPerPixel = 10;

// 5. Тип сцинтиллятора
G4int scintillatorType = 0;  // 0 = CsI(Tl), 1 = YAG(Tb)
```

### Что меняется при изменении параметров:

| Параметр | Влияние |
|----------|---------|
| `pixelSize` | Размер пикселя → автоматически масштабируется вся установка (детектор, сцинтиллятор, полоски, область стрельбы) |
| `gridSize` | Количество пикселей → влияет на область стрельбы и общее число событий |
| `slitWidth` | Ширина золотых полосок и зазоров |
| `particlesPerPixel` | Статистика → больше частиц = лучше статистика, но дольше |
| `scintillatorType` | Тип сцинтиллятора: 0=CsI(Tl), 1=YAG(Tb) |

### Примеры:

**Высокое разрешение:**
```cpp
G4double pixelSize = 5. * um;
G4int gridSize = 200;
```

**Быстрый тест:**
```cpp
G4int gridSize = 50;
G4int particlesPerPixel = 1;
```

**Другой сцинтиллятор:**
```cpp
G4int scintillatorType = 1;  // YAG(Tb) вместо CsI(Tl)
```

---

## 📊 Постобработка

### `build_xray_scintillation.py`

Создает 4 изображения:
1. Карта количества оптических фотонов
2. Рентгеновское изображение (аттенюация)
3. Отношение сигнал/фон (I/I₀)
4. Геометрия (золотые полоски)

**Запуск:**
```bash
cd build
python3 build_xray_scintillation.py
```

**Результаты:**
- `xray_scint_full.png` — все 4 изображения
- `xray_scint_attenuation.png` — только аттенюация (крупно)
- `xray_scint_counts.png` — только количество фотонов (крупно)
- `xray_scint_data.npz` — данные для анализа

### `snr_analysis.py`

Анализ соотношения сигнал/шум по фоновым пикселям.

**Запуск:**
```bash
cd build
python3 snr_analysis.py
```

**Результаты:**
- `snr_histogram.png` — гистограмма распределения фотонов
- `snr_results.txt` — текстовые результаты

### `oimg.py`

Простая визуализация (альтернатива `build_xray_scintillation.py`).

**Запуск:**
```bash
cd build
python3 oimg.py
```

**Результаты:**
- `xray_image.png` — рентгеновское изображение
- `xray_data.npz` — данные

---

## 🔄 Полный рабочий цикл

**Единичный запуск:**
```bash
# 1. Изменить параметры в src/global_parameters.cc
# 2. Сгенерировать mac
cd build
python3 generate_mac.py

# 3. Запустить симуляцию
./sim one.mac

# 4. Постобработка
python3 build_xray_scintillation.py
python3 snr_analysis.py
```

**Пакетный запуск (разные толщины):**
```bash
# 1. Изменить список толщин в run_batch_thickness.sh
# THICKNESSES=(20 100 300)

# 2. Запустить
cd build
bash run_batch_thickness.sh
```

---

## ⚠️ Важные заметки

1. **После изменения `gridSize` или `particlesPerPixel`** — всегда запускайте `python3 generate_mac.py`

2. **После изменения `fCsIThickness`** — необходим `make`

3. **Файл `hits_data.csv`** — создаётся при запуске симуляции, содержит все зарегистрированные частицы

4. **Кодировка** — Python-скрипты автоматически определяют кодировку файла (utf-8, cp1251, latin-1)

5. **Windows PowerShell** — если скрипты не работают в PowerShell, используйте WSL или Git Bash