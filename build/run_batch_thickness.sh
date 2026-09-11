#!/bin/bash
# Скрипт для пакетного прогона симуляции с разными толщинами сцинтиллятора
# Запускать из папки build: bash run_batch_thickness.sh
# Выполняется: generate_mac → симуляция → анализ (изображение, край, SNR)

set -e

# Определяем пути
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$PROJECT_DIR/../src/global_parameters.cc"
RESULTS_DIR="$PROJECT_DIR/results"

# Список толщин для проверки (в мкм)
THICKNESSES=(20 30 40)

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
echo "Измерение: ширина края + SNR vs толщина"
echo "=================================================="

# Проверка наличия файла параметров
if [ ! -f "$PARAMS_FILE" ]; then
    echo "Ошибка: Файл $PARAMS_FILE не найден."
    exit 1
fi

for thickness in "${THICKNESSES[@]}"; do
    echo ""
    echo "=================================================="
    echo "ОБРАБОТКА ТОЛЩИНЫ: ${thickness} мкм"
    echo "=================================================="

    # 1. Изменяем толщину в global_parameters.cc
    echo "Изменяю scintillatorThickness на ${thickness} * um в global_parameters.cc"
    sed -i "s/\(scintillatorThickness = \)[0-9\.]* \* um/\1${thickness} * um/g" "$PARAMS_FILE"
    
    # Проверяем, что замена прошла
    if grep -q "scintillatorThickness = ${thickness} \* um" "$PARAMS_FILE"; then
        echo "  ✓ Значение обновлено."
    else
        echo "  ✗ Ошибка обновления значения. Проверьте формат в global_parameters.cc"
        exit 1
    fi

    # 2. Сборка
    run_step "Сборка (make)" "cd $PROJECT_DIR && make"

    # 3. Очистка данных перед новым запуском
    rm -f "$PROJECT_DIR/hits_data.csv"
    rm -f "$PROJECT_DIR"/xray_*.png
    rm -f "$PROJECT_DIR"/xray_*.npz
    rm -f "$PROJECT_DIR"/edge_profile.png
    rm -f "$PROJECT_DIR"/snr_mask.png
    rm -f "$PROJECT_DIR"/edge_profile_results.txt
    rm -f "$PROJECT_DIR"/snr_results.txt

    # 4. Генерация mac-файла
    run_step "Генерация mac-файла" "cd $PROJECT_DIR && python3 generate_mac.py"

    # 5. Запуск симуляции
    run_step "Запуск симуляции (thick=${thickness}um)" "cd $PROJECT_DIR && ./sim one.mac"

    # 6. Построение рентгеновского изображения
    run_step "Построение изображения" "cd $PROJECT_DIR && python3 analyze_xray_image.py"

    # 7. Анализ края (профиль + erf + FWHM)
    run_step "Анализ края" "cd $PROJECT_DIR && python3 analyze_edge.py $PROJECT_DIR/hits_data.csv"

    # 8. Оценка SNR + маска
    run_step "Оценка SNR" "cd $PROJECT_DIR && python3 analyze_snr.py $PROJECT_DIR/hits_data.csv"

    # 9. Сохранение результатов
    THICK_RESULTS_DIR="$RESULTS_DIR/${thickness}um"
    mkdir -p "$THICK_RESULTS_DIR"
    
    echo "Копирование результатов в $THICK_RESULTS_DIR..."
    
    if [ -f "$PROJECT_DIR/hits_data.csv" ]; then
        cp "$PROJECT_DIR/hits_data.csv" "$THICK_RESULTS_DIR/"
        echo "  ✓ hits_data.csv"
    fi
    
    if [ -f "$PROJECT_DIR/xray_image.png" ]; then
        cp "$PROJECT_DIR/xray_image.png" "$THICK_RESULTS_DIR/"
        echo "  ✓ xray_image.png"
    fi
    
    if [ -f "$PROJECT_DIR/edge_profile.png" ]; then
        cp "$PROJECT_DIR/edge_profile.png" "$THICK_RESULTS_DIR/"
        echo "  ✓ edge_profile.png"
    fi
    
    if [ -f "$PROJECT_DIR/edge_profile_results.txt" ]; then
        cp "$PROJECT_DIR/edge_profile_results.txt" "$THICK_RESULTS_DIR/"
        echo "  ✓ edge_profile_results.txt"
    fi
    
    if [ -f "$PROJECT_DIR/snr_mask.png" ]; then
        cp "$PROJECT_DIR/snr_mask.png" "$THICK_RESULTS_DIR/"
        echo "  ✓ snr_mask.png"
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
Files included: hits_data.csv, edge_profile_results.txt, snr_results.txt
EOF

    echo "✓ Результаты сохранены в: $THICK_RESULTS_DIR"
done

# Финальные графики зависимостей
echo ""
echo "=================================================="
echo "ПОСТРОЕНИЕ ГРАФИКОВ ЗАВИСИМОСТЕЙ"
echo "=================================================="
run_step "Графики зависимостей" "cd $PROJECT_DIR && python3 plot_dependencies.py"

echo ""
echo "=================================================="
echo "✓ ВСЕ ТОЛЩИНЫ ОБРАБОТАНЫ УСПЕШНО!"
echo "Результаты в папке: $RESULTS_DIR"
echo "График зависимостей: resolution_vs_thickness.png"
echo "=================================================="