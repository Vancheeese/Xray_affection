#!/bin/bash
# Скрипт пакетного ПРОГОНА симуляции для разных толщин сцинтиллятора.
# Только генерация mac-файла и симуляция — БЕЗ анализа (analyze_*.py, plot_*).
#
# Устойчив к обрыву SSH: игнорирует SIGHUP, пишет лог в файл и умеет
# продолжаться с места обрыва — готовые толщины пропускаются.
#
# Рекомендуемый запуск (переживает закрытие терминала и обрыв связи):
#   tmux new -s sim
#   bash run_batch_sim_only.sh
#   # отцепиться от сессии: Ctrl-b d   вернуться: tmux attach -t sim
#
# Альтернатива без tmux:
#   nohup bash run_batch_sim_only.sh > /dev/null 2>&1 &
#   tail -f logs/sim_*.log
#
# Возобновление после обрыва: просто запустить скрипт ещё раз.
# Принудительный пересчёт всего:  FORCE=1 bash run_batch_sim_only.sh
# Прогон одной толщины:           ONLY=40 bash run_batch_sim_only.sh

set -e

# Защита от SIGHUP: при обрыве SSH терминал рассылает SIGHUP всем процессам
# своей группы, и прогон умирает посреди симуляции. Игнорируем его — дети
# (make, ./sim) наследуют этот настройк. Остановить вручную: kill -TERM <PID>.
trap '' HUP

# Определяем пути
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARAMS_FILE="$PROJECT_DIR/../src/global_parameters.cc"
RESULTS_DIR="$PROJECT_DIR/results"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/sim_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"
# Весь вывод (включая вывод ./sim) дублируется в лог-файл
exec > >(tee -a "$LOG_FILE") 2>&1

START_TIME=$(date +%s)
echo "Лог: $LOG_FILE"

# Список толщин для прогона (в мкм)
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

# Отпечаток конфигурации прогона: все параметры из global_parameters.cc,
# КРОМЕ scintillatorThickness (он меняется от толщины к толщине). Нужен,
# чтобы при возобновлении не принимать старые данные за новые, если вы
# поменяли энергию, сетку или тип сцинтиллятора.
config_signature() {
    grep -E '^[[:space:]]*G4(double|int)[[:space:]]+(pixelSize|gridSize|slitWidth|particlesPerPixel|scintillatorType|initialEnergy)[[:space:]]*=' "$PARAMS_FILE" \
        | sed 's|//.*||; s/[[:space:]]//g' \
        | md5sum | cut -d' ' -f1
}

# Проверка наличия файла параметров (нужен уже для отпечатка конфигурации)
if [ ! -f "$PARAMS_FILE" ]; then
    echo "Ошибка: Файл $PARAMS_FILE не найден."
    exit 1
fi

CONFIG_SIG="$(config_signature)"
echo "Отпечаток конфигурации: $CONFIG_SIG"

# Толщина считается просчитанной, если рядом с hits_data.csv лежит метка
# .sim_done с тем же отпечатком конфигурации. Метка пишется только после
# успешного копирования, поэтому оборванный прогон её не оставляет.
is_done() {
    local dir="$1"
    [ -f "$dir/hits_data.csv" ] || return 1
    [ -f "$dir/.sim_done" ] || return 1
    [ "$(cat "$dir/.sim_done")" = "$CONFIG_SIG" ] || return 1
    return 0
}

echo "=================================================="
echo "ПАКЕТНАЯ СИМУЛЯЦИЯ: РАЗНЫЕ ТОЛЩИНЫ СЦИНТИЛЛЯТОРА"
echo "Только симуляция (generate_mac + sim), без анализа"
echo "=================================================="

# ONLY=40 — прогнать только одну толщину
RUN_LIST=("${THICKNESSES[@]}")
if [ -n "$ONLY" ]; then
    ONLY="${ONLY%um}"
    RUN_LIST=("$ONLY")
    echo "ONLY=$ONLY — прогоняю только толщину ${ONLY} мкм"
fi

DONE_COUNT=0
SKIP_COUNT=0

for thickness in "${RUN_LIST[@]}"; do
    THICK_DIR="$RESULTS_DIR/${thickness}um"

    echo ""
    echo "=================================================="
    echo "ТОЛЩИНА: ${thickness} мкм"
    echo "=================================================="

    # Пропуск уже просчитанной толщины — это позволяет после обрыва связи
    # запустить скрипт заново и не переделывать сделанное.
    if [ -z "$FORCE" ] && is_done "$THICK_DIR"; then
        echo "Пропускаю ${thickness}um: данные уже есть и конфигурация та же (FORCE=1 для пересчёта)"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        continue
    fi

    # Метку о завершении снимаем до начала счёта: если прогон оборвут,
    # толщина не будет ошибочно принята за готовую.
    rm -f "$THICK_DIR/.sim_done"

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

    # 4. Генерация mac-файла (обязательно, как в основном скрипте)
    run_step "Генерация mac-файла" "cd $PROJECT_DIR && python3 generate_mac.py"

    # 5. Запуск симуляции
    run_step "Запуск симуляции (thick=${thickness}um)" "cd $PROJECT_DIR && ./sim one.mac"

    # 6. Сохранение данных симуляции
    mkdir -p "$THICK_DIR"

    if [ -f "$PROJECT_DIR/hits_data.csv" ]; then
        cp "$PROJECT_DIR/hits_data.csv" "$THICK_DIR/"
        echo "  ✓ hits_data.csv"
    else
        echo "  ✗ hits_data.csv не найден после симуляции"
        exit 1
    fi

    # Создаем текстовый файл с информацией
    cat > "$THICK_DIR/params.txt" << EOF
Thickness: ${thickness} um
Date: $(date)
Simulated with: Geant4 Batch (sim only, no analysis)
Files included: hits_data.csv
Config signature: $CONFIG_SIG
EOF

    # Метка о завершении пишем ПОСЛЕ копирования данных — по ней прогон
    # опознаёт готовые толщины при возобновлении после обрыва.
    echo "$CONFIG_SIG" > "$THICK_DIR/.sim_done"

    DONE_COUNT=$((DONE_COUNT + 1))
    echo "[$(date +%H:%M:%S)] ✓ Данные сохранены в: $THICK_DIR"
done

echo ""
echo "=================================================="
echo "✓ ВСЕ ТОЛЩИНЫ ПРОГНАНЫ УСПЕШНО!"
echo "Просчитано: $DONE_COUNT, пропущено: $SKIP_COUNT"
echo "Время: $(( ($(date +%s) - START_TIME) / 60 )) мин"
echo "Данные в папке: $RESULTS_DIR"
echo "Лог: $LOG_FILE"
echo "Следующий шаг: bash run_batch_analysis.sh"
echo "=================================================="
