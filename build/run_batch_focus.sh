#!/bin/bash
# Пакетная СИМУЛЯЦИЯ с развёрткой ФОКУСА по глубине сцинтиллятора.
# Толщина сцинтиллятора фиксирована (по умолчанию 1200 мкм).
# Для каждой глубины фокуса (0..1200 мкм с шагом 150 мкм) выполняет:
#   Изменение focusDepthFromBack в global_parameters.cc
#   make  ->  generate_mac.py  ->  ./sim one.mac
#   Сохранение hits_data.csv в results/focus_XXXXum/
#
# Запуск:
#   tmux new -s focus
#   bash run_batch_focus.sh
#   # отцепиться: Ctrl-b d; вернуться: tmux attach -t focus
#
# Возобновление после обрыва: просто запустить скрипт заново.
# Полный пересчёт:                FORCE=1 bash run_batch_focus.sh
# Одна глубина:                    ONLY=600 bash run_batch_focus.sh

set -e

trap '' HUP

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$PROJECT_DIR/../src/global_parameters.cc"
RESULTS_DIR="$PROJECT_DIR/results"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/focus_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

START_TIME=$(date +%s)
echo "Лог: $LOG_FILE"

# Глубины фокуса от задней поверхности (в мкм)
FOCUS_DEPTHS=(0 150 300 450 600 750 900 1050 1200)

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
        echo "[$(date +%H:%M:%S)] Выполнение (попытка $((retry + 1))/$max_retries)..."
        echo "Команда: $command"

        if eval "$command"; then
            echo "[$(date +%H:%M:%S)] ✓ $step_name выполнен успешно"
            return 0
        else
            echo "[$(date +%H:%M:%S)] ✗ Ошибка в шаге $step_name"
            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                echo "Повтор через 2 секунды..."
                sleep 2
            fi
        fi
    done

    echo "✗✗✗ КРИТИЧЕСКАЯ ОШИБКА: $step_name не выполнен после $max_retries попыток"
    exit 1
}

if [ ! -f "$PARAMS_FILE" ]; then
    echo "Ошибка: Файл $PARAMS_FILE не найден."
    exit 1
fi

# Отпечаток конфигурации (исключая focusDepthFromBack и scintillatorThickness)
config_signature() {
    grep -E '^[[:space:]]*G4(double|int)[[:space:]]+(pixelSize|gridSize|slitWidth|particlesPerPixel|initialEnergy)[[:space:]]*=' "$PARAMS_FILE" \
        | sed 's|//.*||; s/[[:space:]]//g' \
        | md5sum | cut -d' ' -f1
}

CONFIG_SIG="$(config_signature)"
echo "Отпечаток конфигурации: $CONFIG_SIG"

is_done() {
    local dir="$1"
    [ -f "$dir/hits_data.csv" ] || return 1
    [ -f "$dir/.sim_done" ] || return 1
    [ "$(cat "$dir/.sim_done")" = "$CONFIG_SIG" ] || return 1
    return 0
}

echo "=================================================="
echo "РАЗВЁРТКА ФОКУСА ПО ГЛУБИНЕ СЦИНТИЛЛЯТОРА"
echo "=================================================="

RUN_LIST=("${FOCUS_DEPTHS[@]}")
if [ -n "$ONLY" ]; then
    RUN_LIST=("$ONLY")
    echo "ONLY=$ONLY — прогоняю только глубину ${ONLY} мкм"
fi

DONE_COUNT=0
SKIP_COUNT=0

for depth in "${RUN_LIST[@]}"; do
    # Имя папки — 4 цифры глубины от задней поверхности
    DEPTH_PAD=$(printf "%04d" "$depth")
    THICK_DIR="$RESULTS_DIR/focus_${DEPTH_PAD}um"

    echo ""
    echo "=================================================="
    echo "ГЛУБИНА ФОКУСА: ${depth} мкм от задней поверхности"
    echo "=================================================="

    if [ -z "$FORCE" ] && is_done "$THICK_DIR"; then
        echo "Пропускаю ${depth}um: данные уже есть (FORCE=1 для пересчёта)"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        continue
    fi

    rm -f "$THICK_DIR/.sim_done"

    # 1. Обновляем focusDepthFromBack в global_parameters.cc
    echo "Устанавливаю focusDepthFromBack = ${depth} * um"
    if grep -q "focusDepthFromBack" "$PARAMS_FILE"; then
        sed -i "s/\(focusDepthFromBack = \)[0-9.]* \* um/\1${depth}.0 * um/g" "$PARAMS_FILE"
    else
        echo "  ⚠ Переменная focusDepthFromBack не найдена — добавляю в конец файла"
        echo "" >> "$PARAMS_FILE"
        echo "// Глубина фокуса от задней поверхности сцинтиллятора" >> "$PARAMS_FILE"
        echo "G4double focusDepthFromBack = ${depth}.0 * um;" >> "$PARAMS_FILE"
    fi

    if grep -q "focusDepthFromBack = ${depth}\.0 \* um" "$PARAMS_FILE"; then
        echo "  ✓ Значение обновлено."
    else
        echo "  ✗ Ошибка обновления focusDepthFromBack"
        exit 1
    fi

    # 2. Сборка
    run_step "Сборка (make)" "cd $PROJECT_DIR && make"

    # 3. Очистка данных перед новым запуском
    rm -f "$PROJECT_DIR/hits_data.csv"

    # 4. Генерация mac-файла
    run_step "Генерация mac-файла" "cd $PROJECT_DIR && python3 generate_mac.py"

    # 5. Запуск симуляции
    run_step "Запуск симуляции (focus=${depth}um)" "cd $PROJECT_DIR && ./sim one.mac"

    # 6. Сохранение данных
    mkdir -p "$THICK_DIR"

    if [ -f "$PROJECT_DIR/hits_data.csv" ]; then
        cp "$PROJECT_DIR/hits_data.csv" "$THICK_DIR/"
        echo "  ✓ hits_data.csv"
    else
        echo "  ✗ hits_data.csv не найден после симуляции"
        exit 1
    fi

    cat > "$THICK_DIR/params.txt" << EOF
Focus depth from back surface: ${depth} um
Scintillator thickness: (см. global_parameters.cc)
Date: $(date)
Simulated with: Geant4 Batch (focus sweep)
Files included: hits_data.csv
Config signature: $CONFIG_SIG
EOF

    echo "$CONFIG_SIG" > "$THICK_DIR/.sim_done"

    DONE_COUNT=$((DONE_COUNT + 1))
    echo "[$(date +%H:%M:%S)] ✓ Данные сохранены в: $THICK_DIR"
done

echo ""
echo "=================================================="
echo "✓ ВСЕ ГЛУБИНЫ ПРОГНАНЫ!"
echo "Просчитано: $DONE_COUNT, пропущено: $SKIP_COUNT"
echo "Время: $(( ($(date +%s) - START_TIME) / 60 )) мин"
echo "Данные в папке: $RESULTS_DIR"
echo "Лог: $LOG_FILE"
echo "Следующий шаг: bash run_batch_analysis.sh"
echo "=================================================="