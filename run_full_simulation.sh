#!/bin/bash

# Скрипт автоматизации: генерация mac -> сборка -> симуляция -> визуализация
# Запускать из корня проекта: bash run_full_simulation.sh

set -e  # Остановка при первой ошибке

# Определяем корневую директорию проекта (где находится CMakeLists.txt)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"

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

# Проверка, что мы в корневой директории проекта
if [ ! -f "$PROJECT_ROOT/CMakeLists.txt" ]; then
    echo "Ошибка: CMakeLists.txt не найден. Запускайте скрипт из корня проекта."
    exit 1
fi

# Переходим в корень проекта
cd "$PROJECT_ROOT"

echo "=================================================="
echo "АВТОМАТИЗАЦИЯ СИМУЛЯЦИИ GEANT4"
echo "=================================================="

# Шаг 1: Генерация mac-файла
run_step "Генерация mac-файла" "cd $BUILD_DIR && python3 generate_mac.py"

# Шаг 2: Сборка проекта
run_step "Сборка проекта (make)" "cd $BUILD_DIR && make"

# Шаг 3: Запуск симуляции (с защитой от аварийного завершения при очистке)
run_step "Запуск симуляции" "cd $BUILD_DIR && ./sim one.mac || true"

# Проверка, что данные успешно записаны
if [ ! -f "$BUILD_DIR/hits_data.csv" ]; then
    echo "✗✗✗ ОШИБКА: Файл hits_data.csv не создан после симуляции!"
    exit 1
fi
echo "✓ hits_data.csv успешно создан."

# Шаг 4: Построение изображения
run_step "Построение рентгеновского изображения" "cd $BUILD_DIR && python3 build_xray_image.py"

# Шаг 5: Оценка соотношения сигнал/шум
run_step "Оценка SNR" "cd $BUILD_DIR && python3 snr_analysis.py"

echo ""
echo "=================================================="
echo "✓ ВСЕ ШАГИ ВЫПОЛНЕНЫ УСПЕШНО!"
echo "=================================================="
echo "Результаты:"
echo "  - one.mac (макрос)"
echo "  - sim (исполняемый файл)"
echo "  - xray_counts.png (карта фотонов)"
echo "  - xray_attenuation.png (рентгеновское изображение)"
echo "  - snr_histogram.png (распределение SNR)"
echo "  - *.npz (данные)"
echo "=================================================="
