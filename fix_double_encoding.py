def fix_file(filename):
    try:
        # Читаем файл как cp1251 (получаем искажённую строку)
        with open(filename, 'r', encoding='cp1251') as f:
            corrupted = f.read()
        
        # Кодируем обратно в cp1251 → получаем байты UTF-8
        utf8_bytes = corrupted.encode('cp1251')
        
        # Декодируем как правильный UTF-8
        fixed = utf8_bytes.decode('utf-8')
        
        # ИСПРАВЛЯЕМ ТОЛЬКО 3 ОПЕЧАТКИ (без регулярных выражений!)
        fixed = fixed.replace("if 'temp_name' in context.user_", "if 'temp_name' in context.user_data:")
        fixed = fixed.replace("if not reading_", "if not reading_data:")
        fixed = fixed.replace("if 'pending_readings' not in context.user_", "if 'pending_readings' not in context.user_data:")
        
        # Сохраняем в ЧИСТОМ UTF-8
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(fixed)
        
        print(f"✅ {filename} исправлен от двойного кодирования")
        return True
    except Exception as e:
        print(f"❌ Ошибка {filename}: {e}")
        return False

# Исправляем оба файла
print("🔧 Исправление двойного кодирования...\n")
fix_file('handlers.py')
fix_file('utils.py')
print("\n✨ Готово! Проверяйте синтаксис:")
print("   python -m py_compile bot.py handlers.py utils.py")