import os
import re

def fix_file(filename):
    try:
        # Читаем файл в бинарном режиме
        with open(filename, 'rb') as f:
            content_bytes = f.read()
        
        # Декодируем (пробуем cp1251, если не получится — latin-1)
        try:
            content = content_bytes.decode('cp1251')
        except:
            content = content_bytes.decode('latin-1', errors='ignore')
        
        # ИСПРАВЛЯЕМ ТОЛЬКО КОНКРЕТНЫЕ ОПЕЧАТКИ (с регулярными выражениями)
        # Заменяем ТОЛЬКО те места, где после "reading_" нет "data"
        content = re.sub(r"if not reading_(?!\w)", "if not reading_data:", content)
        content = re.sub(r"if 'temp_name' in context\.user_(?!\w)", "if 'temp_name' in context.user_data:", content)
        content = re.sub(r"if 'pending_readings' not in context\.user_(?!\w)", "if 'pending_readings' not in context.user_data:", content)
        
        # Сохраняем в UTF-8 БЕЗ BOM
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ {filename} исправлен и сохранён в UTF-8")
        return True
    except Exception as e:
        print(f"❌ Ошибка при обработке {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False

# Исправляем оба файла
print("🔧 Исправление кодировки файлов...\n")
fix_file('handlers.py')
fix_file('utils.py')
print("\n✨ Готово! Теперь проверьте синтаксис:")
print("   python -m py_compile bot.py handlers.py utils.py")