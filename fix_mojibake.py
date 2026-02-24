import ftfy

def fix_file(filename):
    """Исправляет кракозябры в строковых литералах файла"""
    try:
        # Читаем файл
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Исправляем кракозябры
        fixed_content = ftfy.fix_text(content)
        
        # Сохраняем обратно
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"✅ {filename} исправлен от кракозябр")
        return True
    except Exception as e:
        print(f"❌ Ошибка {filename}: {e}")
        return False

# Исправляем оба файла
print("🔧 Исправление кракозябр в строковых литералах...\n")
fix_file('handlers.py')
fix_file('utils.py')
print("\n✨ Готово! Теперь проверьте синтаксис:")
print("   python -m py_compile bot.py handlers.py utils.py")