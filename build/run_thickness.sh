#!/bin/bash

# ============================================
# Автоматический запуск симуляций для разных толщин CsI
# ЗАПУСКАТЬ ИЗ ПАПКИ build!
# Структура:
#   ../src/PMDetectorConstruction.cc
#   ../include/PMDetectorConstruction.hh
#   ./sim
#   ./one.mac
# ============================================

# Определяем директории
BUILD_DIR="$(pwd)"
ROOT_DIR="$(cd "$BUILD_DIR/.." && pwd)"
SRC_DIR="$ROOT_DIR/src"
INCLUDE_DIR="$ROOT_DIR/include"

echo "Корневая директория: $ROOT_DIR"
echo "SRC директория: $SRC_DIR"
echo "BUILD директория: $BUILD_DIR"

# Проверяем наличие необходимых файлов
if [ ! -f "$SRC_DIR/PMDetectorConstruction.cc" ]; then
    echo "❌ ОШИБКА: Файл PMDetectorConstruction.cc не найден в $SRC_DIR"
    echo "Содержимое $SRC_DIR:"
    ls -la "$SRC_DIR/"
    exit 1
fi

if [ ! -f "$BUILD_DIR/sim" ]; then
    echo "❌ ОШИБКА: Исполняемый файл sim не найден в $BUILD_DIR"
    exit 1
fi

if [ ! -f "$BUILD_DIR/one.mac" ]; then
    echo "❌ ОШИБКА: Файл one.mac не найден в $BUILD_DIR"
    exit 1
fi

# Создаём папку для результатов в корневой директории
RESULTS_DIR="$ROOT_DIR/build/results"
mkdir -p "$RESULTS_DIR"

# Толщины для исследования (микроны)
THICKNESSES=(10 25 50 75 100 150 200 300 500)

# Максимум попыток для каждой толщины
MAX_RETRIES=2

# Файл для логирования
LOG_FILE="$RESULTS_DIR/simulation_log.txt"

echo "=========================================" | tee -a "$LOG_FILE"
echo "Запуск: $(date)" | tee -a "$LOG_FILE"
echo "Корневая директория: $ROOT_DIR" | tee -a "$LOG_FILE"
echo "SRC директория: $SRC_DIR" | tee -a "$LOG_FILE"
echo "Результаты в: $RESULTS_DIR" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"

# Функция проверки, успешно ли выполнена симуляция для толщины
is_simulation_done() {
    local thick=$1
    local file="$RESULTS_DIR/hits_data_${thick}um.csv"
    
    if [ -f "$file" ] && [ -s "$file" ]; then
        local size=$(stat -c%s "$file")
        if [ $size -gt 1024 ]; then
            return 0
        fi
    fi
    return 1
}

# Функция запуска симуляции для одной толщины
run_simulation_for_thickness() {
    local thick=$1
    local attempt=$2
    
    echo "----------------------------------------" | tee -a "$LOG_FILE"
    echo "[$(date)] Толщина CsI: ${thick} мкм (попытка $attempt)" | tee -a "$LOG_FILE"
    echo "----------------------------------------" | tee -a "$LOG_FILE"
    
    # 1. Меняем толщину в коде (файл в src директории)
    cd "$SRC_DIR"
    sed -i "s/G4double csiThickness = [0-9]* \* um;/G4double csiThickness = ${thick} * um;/" PMDetectorConstruction.cc
    echo "✅ Изменена толщина на ${thick} мкм в $SRC_DIR/PMDetectorConstruction.cc" | tee -a "$LOG_FILE"
    
    # 2. Компилируем (из build директории)
    cd "$BUILD_DIR"
    echo "🔨 Компиляция..." | tee -a "$LOG_FILE"
    
    # Очищаем и компилируем
    make clean > /dev/null 2>&1
    
    if make -j2 2>&1 | tee -a "$LOG_FILE"; then
        echo "✅ Компиляция успешна" | tee -a "$LOG_FILE"
    else
        echo "❌ Ошибка компиляции для ${thick} мкм" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # 3. Запускаем симуляцию (из build директории)
    echo "🎯 Запуск симуляции..." | tee -a "$LOG_FILE"
    
    ./sim one.mac > "/tmp/sim_output_${thick}.log" 2>&1
    
    SIM_EXIT_CODE=$?
    
    if [ $SIM_EXIT_CODE -eq 0 ]; then
        # Проверяем создался ли файл hits_data.csv в build директории
        if [ -f "$BUILD_DIR/hits_data.csv" ]; then
            FILE_SIZE=$(stat -c%s "$BUILD_DIR/hits_data.csv")
            if [ $FILE_SIZE -gt 1024 ]; then
                mv "$BUILD_DIR/hits_data.csv" "$RESULTS_DIR/hits_data_${thick}um.csv"
                echo "✅ УСПЕХ: ${thick} мкм (размер: $FILE_SIZE байт)" | tee -a "$LOG_FILE"
                return 0
            else
                echo "⚠️ Файл слишком маленький ($FILE_SIZE байт)" | tee -a "$LOG_FILE"
                rm -f "$BUILD_DIR/hits_data.csv"
            fi
        else
            echo "❌ Файл hits_data.csv не создан в $BUILD_DIR" | tee -a "$LOG_FILE"
            echo "Содержимое $BUILD_DIR:" | tee -a "$LOG_FILE"
            ls -la "$BUILD_DIR/" | tee -a "$LOG_FILE"
        fi
    else
        echo "❌ Ошибка выполнения ./sim (код: $SIM_EXIT_CODE)" | tee -a "$LOG_FILE"
        echo "Последние строки вывода:" | tee -a "$LOG_FILE"
        tail -20 "/tmp/sim_output_${thick}.log" 2>/dev/null | tee -a "$LOG_FILE"
    fi
    
    return 1
}

# ========== ОСНОВНОЙ ЦИКЛ ==========

echo ""
echo "📊 СТАТУС СУЩЕСТВУЮЩИХ РЕЗУЛЬТАТОВ:" | tee -a "$LOG_FILE"
echo "----------------------------------------" | tee -a "$LOG_FILE"

for thick in "${THICKNESSES[@]}"; do
    if is_simulation_done $thick; then
        size=$(stat -c%s "$RESULTS_DIR/hits_data_${thick}um.csv")
        size_mb=$((size / 1048576))
        echo "  ✅ ${thick} мкм - уже есть (${size_mb} MB)" | tee -a "$LOG_FILE"
    else
        echo "  ❌ ${thick} мкм - отсутствует или пустой" | tee -a "$LOG_FILE"
    fi
done

echo ""
echo "🚀 ЗАПУСК НЕДОСТАЮЩИХ СИМУЛЯЦИЙ:" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"

for thick in "${THICKNESSES[@]}"; do
    if is_simulation_done $thick; then
        echo "⏭️ Пропускаем ${thick} мкм (уже есть)" | tee -a "$LOG_FILE"
        continue
    fi
    
    RETRY=0
    SUCCESS=0
    
    while [ $RETRY -lt $MAX_RETRIES ] && [ $SUCCESS -eq 0 ]; do
        if run_simulation_for_thickness $thick $((RETRY+1)); then
            SUCCESS=1
        else
            RETRY=$((RETRY+1))
            if [ $RETRY -lt $MAX_RETRIES ]; then
                echo "⚠️ Повторная попытка через 5 секунд..." | tee -a "$LOG_FILE"
                sleep 5
            fi
        fi
    done
    
    if [ $SUCCESS -eq 0 ]; then
        echo "❌ НЕ УДАЛОСЬ после $MAX_RETRIES попыток для толщины ${thick} мкм" | tee -a "$LOG_FILE"
    fi
    
    echo "" | tee -a "$LOG_FILE"
done

# ========== ИТОГОВЫЙ ОТЧЁТ ==========
echo "=========================================" | tee -a "$LOG_FILE"
echo "✅ ВСЕ СИМУЛЯЦИИ ЗАВЕРШЕНЫ" | tee -a "$LOG_FILE"
echo "Время завершения: $(date)" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "📊 ИТОГОВЫЙ СТАТУС:" | tee -a "$LOG_FILE"
echo "----------------------------------------" | tee -a "$LOG_FILE"

SUCCESS_COUNT=0
for thick in "${THICKNESSES[@]}"; do
    if is_simulation_done $thick; then
        size=$(stat -c%s "$RESULTS_DIR/hits_data_${thick}um.csv")
        size_mb=$((size / 1048576))
        echo "  ✅ ${thick} мкм - ${size_mb} MB" | tee -a "$LOG_FILE"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "  ❌ ${thick} мкм - ПРОБЛЕМА" | tee -a "$LOG_FILE"
    fi
done

echo "----------------------------------------" | tee -a "$LOG_FILE"
echo "Успешно: $SUCCESS_COUNT из ${#THICKNESSES[@]}" | tee -a "$LOG_FILE"
echo "=========================================" | tee -a "$LOG_FILE"

echo ""
echo "📁 Содержимое папки с результатами ($RESULTS_DIR):"
ls -lh "$RESULTS_DIR/"