# Инструменты Metro-14

## validate_rsi.py — проверка RSI и прототипов

Чистый Python 3, без зависимостей (PIL/PyYAML не нужны).

```
python Tools/_Metro14/validate_rsi.py                 # всё: Resources/Textures/_Metro14 + Resources/Prototypes/_Metro14
python Tools/_Metro14/validate_rsi.py path/to/x.rsi   # только указанные .rsi / .yml / папки
```

Вывод: строки `ERROR <путь>: <причина>` и `WARN ...`, в конце сводка.
Код выхода 1, если есть хотя бы одна ERROR, иначе 0.

### Правила RSI
- `meta.json` парсится, есть `version`, `license`, `copyright`, `size.x/size.y`, `states`.
- `directions` только 1, 4 или 8; число списков в `delays` = `directions`.
- У каждого состояния есть `<name>.png`; PNG без состояния — WARN.
- Размер PNG кратен `size`.
- Нужно кадров = сумма длин списков `delays` (пустой список = 1 кадр), без `delays` = `directions`.
- Кадры идут построчно (слева направо, сверху вниз) в сетке, где колонок = `ceil(sqrt(кадров))`.
  Пример: 4 направления = 2x2, а не полоска 4x1; 8 кадров = 3 колонки.

### Правила прототипов (компоненты Sprite и Icon)
- `sprite:` указывает на существующую папку `Resources/Textures/<путь>.rsi`; `state:` есть в её meta.json.
- То же для `layers:` (если у слоя нет `sprite`, берётся спрайт компонента).
- `snapCardinals: true` при состоянии с `directions != 1` — ERROR (ловит DebugAssert в SpriteSystem.Bounds.cs).
- Icon с `directions != 1` — WARN (движок берёт только Frame0, т.е. юг).
- Если `sprite` не задан, ищется у родителей (`parent`) среди просканированных YAML; не найден — WARN.

### Стиль (по Tools/_Metro14/style/STYLE_GUIDE.md)
- Полупрозрачность (alpha не 0 и не 255) разрешена только для стекла, теней, света, оверлеев. Если доля полупрозрачных пикселей в state > 2% от видимых — ERROR.
  Исключения (только WARN): имя state содержит glass, window, shadow, light, lit, glow, overlay, unshaded, emissive;
  либо RSI/state указан в `Tools/_Metro14/rsi_whitelist.txt` (по строке: `_Metro14/Structures/foo.rsi` или `_Metro14/Structures/foo.rsi/state`, можно glob, `#` — комментарий).
- Уникальные цвета на state (непрозрачные): WARN выше лимита гайда — 16 для кадра ≤32 px, 30 для ≤64 px, 300 для крупных (96–128); ERROR выше 2048 (фото/размытие).
- Декодер PNG встроенный (zlib + PNG-фильтры), поддерживает 8-битные RGBA/RGB/палитру/grayscale; иначе проверка пропускается с WARN.
