import sys
import re

def count_phrase_in_file(filename, phrase):
    """Подсчитывает количество вхождений фразы в файле"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
            # Подсчитываем все вхождения (включая перекрывающиеся)
            count = content.count(phrase)
            return count
    except FileNotFoundError:
        print(f"Ошибка: Файл '{filename}' не найден")
        return None
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return None

if __name__ == "__main__":
    # Настройки
    # filename = r"c:\Study\settlement\out.txt"  # Используем сырую строку (r перед кавычками)
    filename = "out.txt"  # Используем сырую строку (r перед кавычками)
    phrase_to_search = "Photon position: (0,0,189)"
    # phrase_to_search = "Photon position:"

    # Выполняем подсчет
    count = count_phrase_in_file(filename, phrase_to_search)
    
    if count is not None:
        print(f"Фраза '{phrase_to_search}' найдена {count} раз(а)")
