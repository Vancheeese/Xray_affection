#!/bin/bash
# Скрипт для пакетного прогона симуляции с разными толщинами сцинтиллятора
# Запускать из папки build: bash run_batch_thickness.sh

set -e

# Определяем пути
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$PROJECT_DIR/../include"
RESULTS_DIR="$PROJECT_DIR/results"

# Файл, который будем менять
HEADER_FILE="$SRC_DIR/PMDetectorConstruction.hh"

# Список толщин для проверки (в мкм)
THICKNESSES=(20 25 30 35 40 45 50)

# Функция для выполнения шага с повтором при ошибке
run_step() {
    local step_name="$1"
    local command="$2"
    local max_retries=3
    local retry=0
    
    echo ""
    echo "=========================================="
    echo "ШАГ: $step_name"
    echo "=========================================="
    
    while [ $retry -lt $max_retries ]; do
        echo "Выполнение (попытка $((retry + 1))/$max_retries)..."
        echo "Команда: $command"
        
        if eval "$command"; then
            echo "✓ $step_name выполнен успешно"
            return 0
        else
            echo "✗ Ошибка в шаге $step_name"
            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                echo "Повтор через 2 секунды..."
                sleep 2
            fi
        fi
    done
    
    echo "✗✗✗ КРИТИЧЕСКАЯ ОШИБКА: $step_name не выполнен после $max_retries попыток"
    echo "Останавливаю выполнение."
    exit 1
}

echo "=================================================="
echo "ПАКЕТНАЯ СИМУЛЯЦИЯ: РАЗНЫЕ ТОЛЩИНЫ СЦИНТИЛЛЯТОРА"
echo "=================================================="

# Проверка наличия исходников
if [ ! -f "$HEADER_FILE" ]; then
    echo "Ошибка: Файл $HEADER_FILE не найден."
    exit 1
fi

for thickness in "${THICKNESSES[@]}"; do
    echo ""
    echo "=================================================="
    echo "ОБРАБОТКА ТОЛЩИНЫ: ${thickness} мкм"
    echo "=================================================="

    # 1. Изменяем толщину в заголовочном файле
    echo "Изменяю fCsIThickness на ${thickness} * um в PMDetectorConstruction.hh"
    # Используем sed для замены значения по умолчанию (ищем число перед * um)
    sed -i "s/\(fCsIThickness = \)[0-9\.]* \* um/\1${thickness} * um/g" "$HEADER_FILE"
    
    # Проверяем, что замена прошла
    if grep -q "fCsIThickness = ${thickness} \* um" "$HEADER_FILE"; then
        echo "  ✓ Значение обновлено."
    else
        echo "  ✗ Ошибка обновления значения. Проверьте формат в хедере."
        exit 1
    fi

    # 2. Сборка
    run_step "Сборка (make)" "cd $PROJECT_DIR && make"

    # 3. Очистка данных перед новым запуском
    rm -f "$PROJECT_DIR/hits_data.csv"
    rm -f "$PROJECT_DIR"/xray_*.png
    rm -f "$PROJECT_DIR"/xray_*.npz
    rm -f "$PROJECT_DIR"/snr_histogram.png
    rm -f "$PROJECT_DIR"/snr_results.txt

    # 4. Запуск симуляции
    run_step "Запуск симуляции (thick=${thickness}um)" "cd $PROJECT_DIR && ./sim one.mac"

    # 5. Построение рентгеновского изображения
    run_step "Генерация рентгеновского изображения" "cd $PROJECT_DIR && python3 build_xray_image.py"

    # 6. Анализ SNR
    run_step "Анализ SNR" "cd $PROJECT_DIR && python3 snr_analysis.py"

    # 7. Сохранение результатов
    THICK_RESULTS_DIR="$RESULTS_DIR/${thickness}um"
    mkdir -p "$THICK_RESULTS_DIR"
    
    echo "Копирование результатов в $THICK_RESULTS_DIR..."
    
    # Копируем hits_data.csv
    if [ -f "$PROJECT_DIR/hits_data.csv" ]; then
        cp "$PROJECT_DIR/hits_data.csv" "$THICK_RESULTS_DIR/"
        echo "  ✓ hits_data.csv"
    else
        echo "  ✗ hits_data.csv не найден"
    fi
    
    # Копируем xray_*.png
    for f in "$PROJECT_DIR"/xray_*.png; do
        if [ -f "$f" ]; then
            cp "$f" "$THICK_RESULTS_DIR/"
            echo "  ✓ $(basename "$f")"
        fi
    done
    
    # Копируем xray_*.npz
    for f in "$PROJECT_DIR"/xray_*.npz; do
        if [ -f "$f" ]; then
            cp "$f" "$THICK_RESULTS_DIR/"
            echo "  ✓ $(basename "$f")"
        fi
    done
    
    # Копируем snr_histogram.png
    if [ -f "$PROJECT_DIR/snr_histogram.png" ]; then
        cp "$PROJECT_DIR/snr_histogram.png" "$THICK_RESULTS_DIR/"
        echo "  ✓ snr_histogram.png"
    else
        echo "  ✗ snr_histogram.png не найден"
    fi
    
    # Копируем snr_results.txt
    if [ -f "$PROJECT_DIR/snr_results.txt" ]; then
        cp "$PROJECT_DIR/snr_results.txt" "$THICK_RESULTS_DIR/"
        echo "  ✓ snr_results.txt"
    else
        echo "  ✗ snr_results.txt не найден"
    fi
    
    # Копируем xray_*.png
    for f in "$PROJECT_DIR"/xray_*.png; do
        if [ -f "$f" ]; then
            cp "$f" "$THICK_RESULTS_DIR/"
            echo "  ✓ $(basename "$f")"
        fi
    done
    
    # Копируем xray_*.npz
    for f in "$PROJECT_DIR"/xray_*.npz; do
        if [ -f "$f" ]; then
            cp "$f" "$THICK_RESULTS_DIR/"
            echo "  ✓ $(basename "$f")"
        fi
    done
    
    # Копируем snr_histogram.png
    if [ -f "$PROJECT_DIR/snr_histogram.png" ]; then
        cp "$PROJECT_DIR/snr_histogram.png" "$THICK_RESULTS_DIR/"
        echo "  ✓ snr_histogram.png"
    else
        echo "  ✗ snr_histogram.png не найден"
    fi
    
    # Копируем snr_results.txt
    if [ -f "$PROJECT_DIR/snr_results.txt" ]; then
        cp "$PROJECT_DIR/snr_results.txt" "$THICK_RESULTS_DIR/"
        echo "  ✓ snr_results.txt"
    else
        echo "  ✗ snr_results.txt не найден"
    fi
    
    for f in "$PROJECT_DIR"/xray_*.png; do
        if [ -f "$f" ]; then
            cp "$f" "$THICK_RESULTS_DIR/"
            echo "  ✓ $(basename $f)"
        fi
    done
    
    for f in "$PROJECT_DIR"/xray_*.npz; do
        if [ -f "$f" ]; then
            cp "$f" "$THICK_RESULTS_DIR/"
            echo "  ✓ $(basename $f)"
        fi
    done
    
    if [ -f "$PROJECT_DIR/snr_histogram.png" ]; then
        cp "$PROJECT_DIR/snr_histogram.png" "$THICK_RESULTS_DIR/"
        echo "  ✓ snr_histogram.png"
    fi
    
    if [ -f "$PROJECT_DIR/snr_results.txt" ]; then
        cp "$PROJECT_DIR/snr_results.txt" "$THICK_RESULTS_DIR/"
        echo "  ✓ snr_results.txt"
    fi
    
    # Создаем текстовый файл с информацией
    cat > "$THICK_RESULTS_DIR/params.txt" << EOF
Thickness: ${thickness} um
Date: $(date)
Simulated with: Geant4 Batch
Files included: hits_data.csv, xray_*.png, snr_histogram.png
EOF

    echo "✓ Результаты сохранены в: $THICK_RESULTS_DIR"
done

echo ""
echo "=================================================="
echo "✓ ВСЕ ТОЛЩИНЫ ОБРАБОТАНЫ УСПЕШНО!"
echo "Результаты в папке: $RESULTS_DIR"
echo "=================================================="