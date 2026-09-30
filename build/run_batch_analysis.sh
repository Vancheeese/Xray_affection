#!/bin/bash
# Пакетный АНАЛИЗ результатов симуляции из build/results.
# Для каждой папки толщины (20um, 30um, 40um, ...) выполняет:
#   analyze_xray_image.py, analyze_snr.py, analyze_edge.py
# В конце один раз — plot_dependencies.py (общий график по всем толщинам).
# Симуляцию НЕ запускает, работает только с существующими hits_data.csv.
#
# Устойчив к обрыву SSH: пишет лог в файл. Запускать так:
#   nohup bash run_batch_analysis.sh > /dev/null 2>&1 &
#   tail -f logs/analysis_*.log
# Результаты snr/edge при повторном запуске всегда перезаписываются.
# Пересчёт одной толщины: ONLY=30um bash run_batch_analysis.sh

set -e

# Защита от SIGHUP: при обрыве SSH терминал рассылает SIGHUP всем процессам
# своей группы, и скрипт умирает посреди прогона. Игнорируем его — дети
# (python3) наследуют этот настройк. Остановить вручную: kill -TERM <PID>.
trap '' HUP

# Определяем пути
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$PROJECT_DIR/results"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/analysis_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"
# Весь вывод (включая вывод python) дублируется в лог-файл
exec > >(tee -a "$LOG_FILE") 2>&1

START_TIME=$(date +%s)
echo "Лог: $LOG_FILE"

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
    echo "Останавливаю выполнение. Готовые толщины будут пропущены при следующем запуске."
    exit 1
}

# Признак того, что толщина уже проанализирована: все нужные выходы
# существуют и новее, чем hits_data.csv. Позволяет продолжить после обрыва.
# Используется только для статистики: результаты snr и edge при наличии
# ВСЕГДА пересчитываются и перезаписываются (см. цикл ниже).
is_done() {
    local dir="$1"
    local csv="$dir/hits_data.csv"
    local f
    for f in xray_image.png snr_results.txt edge_profile_results.txt; do
        [ -f "$dir/$f" ] || return 1
        [ "$dir/$f" -nt "$csv" ] || return 1
    done
    return 0
}

echo "=================================================="
echo "ПАКЕТНЫЙ АНАЛИЗ ПО ПАПКЕ ТОЛЩИН В $RESULTS_DIR"
echo "=================================================="

if [ ! -d "$RESULTS_DIR" ]; then
    echo "Ошибка: папка $RESULTS_DIR не найдена."
    echo "Сначала выполните симуляцию: bash run_batch_sim_only.sh"
    exit 1
fi

# Собираем папки вида <число>um и сортируем по числовому значению толщины
THICK_DIRS=$(find "$RESULTS_DIR" -mindepth 1 -maxdepth 1 -type d -name '*um' | sort -V)

if [ -z "$THICK_DIRS" ]; then
    echo "Ошибка: в $RESULTS_DIR нет папок с толщиной (*um)."
    exit 1
fi

# ONLY=30um — обработать только одну толщину
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

    echo ""
    echo "=================================================="
    echo "АНАЛИЗ: $THICK_NAME"
    echo "=================================================="

    if [ ! -f "$CSV" ]; then
        echo "Пропускаю $THICK_NAME: нет hits_data.csv"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        continue
    fi

    # Результаты snr и edge НЕ пропускаем: если старые snr_results.txt /
    # edge_profile_results.txt уже лежат в папке — перезаписываем их свежими
    # (анализ идемпотентен, работает по одному и тому же hits_data.csv).
    if [ -f "$THICK_DIR/snr_results.txt" ] || [ -f "$THICK_DIR/edge_profile_results.txt" ]; then
        echo "Найдены предыдущие результаты SNR/edge в $THICK_NAME — перезаписываю"
    fi

    # Подчищаем временные файлы после прерванного запуска
    rm -f "$CSV.tmp.npy"

    # python3 -u: небуферизованный вывод, чтобы лог заполнялся по ходу дела
    # 1. Рентгеновское изображение
    run_step "Построение изображения ($THICK_NAME)" \
        "cd $PROJECT_DIR && python3 -u analyze_xray_image.py $CSV"

    # 2. Оценка SNR + маска
    run_step "Оценка SNR ($THICK_NAME)" \
        "cd $PROJECT_DIR && python3 -u analyze_snr.py $CSV"

    # 3. Анализ края (профиль + erf + FWHM)
    run_step "Анализ края ($THICK_NAME)" \
        "cd $PROJECT_DIR && python3 -u analyze_edge.py $CSV"

    DONE_COUNT=$((DONE_COUNT + 1))
    echo "[$(date +%H:%M:%S)] ✓ Анализ $THICK_NAME завершён, результаты в: $THICK_DIR"
done

# 4. Итоговые графики зависимостей FWHM/SNR от толщины (по всем папкам сразу)
echo ""
echo "=================================================="
echo "ПОСТРОЕНИЕ ГРАФИКОВ ЗАВИСИМОСТЕЙ"
echo "=================================================="
if [ -f "$PROJECT_DIR/plot_dependencies.py" ]; then
    run_step "Графики зависимостей" "cd $PROJECT_DIR && python3 plot_dependencies.py"
    PLOT_RESULT="$PROJECT_DIR/resolution_vs_thickness.png"
else
    echo "Пропущено: $PROJECT_DIR/plot_dependencies.py не найден"
    PLOT_RESULT="не построен (plot_dependencies.py отсутствует)"
fi

echo ""
echo "=================================================="
echo "✓ АНАЛИЗ ВСЕХ ТОЛЩИН ЗАВЕРШЁН!"
echo "Просчитано: $DONE_COUNT, пропущено: $SKIP_COUNT"
echo "Время: $(( ($(date +%s) - START_TIME) / 60 )) мин"
echo "Результаты в папке: $RESULTS_DIR"
echo "График зависимостей: $PLOT_RESULT"
echo "Лог: $LOG_FILE"
echo "=================================================="
