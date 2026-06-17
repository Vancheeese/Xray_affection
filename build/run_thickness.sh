#!/bin/bash

# ============================================
# Запуск симуляций для разных толщин CsI
# С ПРОВЕРКОЙ уже существующих результатов
# ============================================

# Создаём папку для результатов
RESULTS_DIR="./results"
mkdir -p "$RESULTS_DIR"

# Толщины для исследования (мкм)
THICKNESSES=(50 100 150 200 300 500)

# Макрос для запуска
MACRO="one.mac"

# Минимальный размер файла (байт) для считаем успешным
MIN_FILE_SIZE=1024

# Проверка наличия исполняемого файла
if [ ! -f "./sim" ]; then
    echo "Ошибка: исполняемый файл sim не найден"
    exit 1
fi

# ========== ФУНКЦИЯ ПРОВЕРКИ ==========
is_simulation_done() {
    local thick=$1
    local file="$RESULTS_DIR/hits_data_${thick}um.csv"
    
    if [ -f "$file" ] && [ -s "$file" ]; then
        local size=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null)
        if [ "$size" -gt "$MIN_FILE_SIZE" ]; then
            return 0  # файл существует и достаточно большой
        fi
    fi
    return 1  # файла нет или он слишком маленький
}

# ========== ОСНОВНОЙ ЦИКЛ ==========

echo "========================================="
echo "Запуск симуляций для толщин: ${THICKNESSES[*]} мкм"
echo "========================================="

# Проверяем статус существующих файлов
echo ""
echo "Статус существующих результатов:"
echo "----------------------------------------"

to_run=()
for t in "${THICKNESSES[@]}"; do
    if is_simulation_done $t; then
        size=$(stat -c%s "$RESULTS_DIR/hits_data_${t}um.csv" 2>/dev/null || stat -f%z "$RESULTS_DIR/hits_data_${t}um.csv" 2>/dev/null)
        size_kb=$((size / 1024))
        echo "  ✅ ${t} мкм - уже есть (${size_kb} KB)"
    else
        echo "  ❌ ${t} мкм - отсутствует"
        to_run+=($t)
    fi
done

# Запускаем только недостающие
if [ ${#to_run[@]} -eq 0 ]; then
    echo ""
    echo "✅ Все симуляции уже выполнены!"
else
    echo ""
    echo "🚀 Запуск недостающих симуляций:"
    echo "========================================="
    
    for t in "${to_run[@]}"; do
        echo ""
        echo "Запуск для толщины ${t} мкм..."
        
        # Удаляем старый файл перед запуском
        rm -f "hits_data.csv"
        
        # Запускаем симуляцию
        ./sim "$MACRO" "$t"
        
        # Проверяем результат
        if [ -f "hits_data.csv" ]; then
            size=$(stat -c%s "hits_data.csv" 2>/dev/null || stat -f%z "hits_data.csv" 2>/dev/null)
            if [ "$size" -gt "$MIN_FILE_SIZE" ]; then
                mv "hits_data.csv" "$RESULTS_DIR/hits_data_${t}um.csv"
                echo "✅ Сохранено: hits_data_${t}um.csv (${size} байт)"
            else
                echo "⚠️ Файл слишком маленький (${size} байт), удаляем"
                rm -f "hits_data.csv"
            fi
        else
            echo "❌ Файл hits_data.csv не создан"
        fi
    done
fi

# ========== ИТОГОВЫЙ ОТЧЁТ ==========
echo ""
echo "========================================="
echo "Итоговый статус:"
echo "----------------------------------------"
success_count=0
for t in "${THICKNESSES[@]}"; do
    if is_simulation_done $t; then
        size=$(stat -c%s "$RESULTS_DIR/hits_data_${t}um.csv" 2>/dev/null || stat -f%z "$RESULTS_DIR/hits_data_${t}um.csv" 2>/dev/null)
        size_kb=$((size / 1024))
        echo "  ✅ ${t} мкм - ${size_kb} KB"
        success_count=$((success_count + 1))
    else
        echo "  ❌ ${t} мкм - ПРОБЛЕМА"
    fi
done

echo "----------------------------------------"
echo "Успешно: $success_count из ${#THICKNESSES[@]}"
echo "========================================="
echo ""
echo "Содержимое папки с результатами:"
ls -lh "$RESULTS_DIR/"