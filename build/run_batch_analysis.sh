#!/bin/bash
# Пакетный АНАЛИЗ результатов симуляции из build/results.
# Для каждой папки толщины (20um, 30um, 40um, ...) выполняет:
#   xray_image.py  -> michelson.py -> fwhm.py
# Текстовые файлы с результатами (michelson_results.txt, fwhm_results.txt)
# сохраняются рядом с xray_image.npz, то есть в тех же папках, где
# лежит hits_data.csv.
# Симуляцию НЕ запускает, работает только с существующими hits_data.csv.
#
# Устойчив к обрыву SSH: пишет лог в файл. Запускать так:
#   nohup bash run_batch_analysis.sh > /dev/null 2>&1 &
#   tail -f logs/analysis_*.log
# Результаты при повторном запуске всегда перезаписываются.
# Пересчёт одной толщины: ONLY=30um bash run_batch_analysis.sh

set -e

trap '' HUP

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$PROJECT_DIR/results"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/analysis_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

START_TIME=$(date +%s)
echo "Лог: $LOG_FILE"

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
    echo "Останавливаю выполнение."
    exit 1
}

echo "=================================================="
echo "ПАКЕТНЫЙ АНАЛИЗ ПО ПАПКЕ ТОЛЩИН В $RESULTS_DIR"
echo "=================================================="

if [ ! -d "$RESULTS_DIR" ]; then
    echo "Ошибка: папка $RESULTS_DIR не найдена."
    echo "Сначала выполните симуляцию."
    exit 1
fi

THICK_DIRS=$(find "$RESULTS_DIR" -mindepth 1 -maxdepth 1 -type d -name '*um' | sort -V)

if [ -z "$THICK_DIRS" ]; then
    echo "Ошибка: в $RESULTS_DIR нет папок с толщиной (*um)."
    exit 1
fi

if [ -n "$ONLY" ]; then
    THICK_DIRS="$RESULTS_DIR/$ONLY"
    if [ ! -d "$THICK_DIRS" ]; then
        echo "Ошибка: папка $THICK_DIRS не найдена (ONLY=$ONLY)"
        exit 1
    fi
fi

DONE_COUNT=0
SKIP_COUNT=0

for THICK_DIR in $THICK_DIRS; do
    THICK_NAME=$(basename "$THICK_DIR")
    CSV="$THICK_DIR/hits_data.csv"
    NPZ="$THICK_DIR/xray_image.npz"

    echo ""
    echo "=================================================="
    echo "АНАЛИЗ: $THICK_NAME"
    echo "=================================================="

    if [ ! -f "$CSV" ]; then
        echo "Пропускаю $THICK_NAME: нет hits_data.csv"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        continue
    fi

    if [ -f "$THICK_DIR/michelson_results.txt" ] || [ -f "$THICK_DIR/fwhm_results.txt" ]; then
        echo "Найдены предыдущие результаты в $THICK_NAME — перезаписываю"
    fi

    # Подчищаем временные файлы после прерванного запуска
    rm -f "$CSV.tmp.txt"

    # 1. Построение рентгеновского изображения (даёт xray_image.npz и .png)
    run_step "Построение изображения ($THICK_NAME)" \
        "cd $PROJECT_DIR && python3 -u xray_image.py $CSV"

    # Проверка, что npz действительно создался
    if [ ! -f "$NPZ" ]; then
        echo "✗✗✗ КРИТИЧЕСКАЯ ОШИБКА: $NPZ не создан шагом xray_image.py"
        exit 1
    fi

    # 2. Контраст Михельсона (пишет michelson_results.txt рядом с npz)
    run_step "Контраст Михельсона ($THICK_NAME)" \
        "cd $PROJECT_DIR && python3 -u michelson.py $NPZ"

    # 3. FWHM (пишет fwhm_results.txt рядом с npz)
    run_step "FWHM ($THICK_NAME)" \
        "cd $PROJECT_DIR && python3 -u fwhm.py $NPZ"

    DONE_COUNT=$((DONE_COUNT + 1))
    echo "[$(date +%H:%M:%S)] ✓ Анализ $THICK_NAME завершён, результаты в: $THICK_DIR"
done

echo ""
echo "=================================================="
echo "✓ АНАЛИЗ ВСЕХ ТОЛЩИН ЗАВЕРШЁН!"
echo "Просчитано: $DONE_COUNT, пропущено: $SKIP_COUNT"
echo "Время: $(( ($(date +%s) - START_TIME) / 60 )) мин"
echo "Результаты в папке: $RESULTS_DIR"
echo "Лог: $LOG_FILE"
echo "=================================================="