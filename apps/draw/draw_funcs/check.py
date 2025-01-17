import io

import discord
import genshin
from PIL import Image, ImageDraw

import asset
from apps.draw.utility import circular_crop, get_cache, get_font
from apps.text_map.text_map_app import text_map


def card(
    note: genshin.models.Notes,
    locale: discord.Locale | str,
    dark_mode: bool,
) -> io.BytesIO:
    im = Image.open(
        f"yelan/templates/check/[{'dark' if dark_mode else 'light'}] Check.png"
    )
    draw = ImageDraw.Draw(im)

    # title
    font = get_font(locale, 65, "Bold")
    fill = asset.primary_text if not dark_mode else asset.white
    draw.text((81, 64), text_map.get(24, locale), font=font, fill=fill)

    # four squares
    four_squares = {
        text_map.get(4, locale): f"{note.current_resin}/{note.max_resin}",
        text_map.get(
            2, locale
        ): f"{note.current_realm_currency}/{note.max_realm_currency}",
        text_map.get(6, locale): f"{note.completed_commissions}/{note.max_commissions}",
        text_map.get(
            5, locale
        ): f"{note.remaining_resin_discounts}/{note.max_resin_discounts}",
    }
    offset = (113, 383)
    num = 0
    for square, text in four_squares.items():
        num += 1
        if num == 3:
            offset = (113, 783)
        # square
        fill = asset.secondary_text if not dark_mode else asset.white
        font = get_font(locale, 35)
        draw.text(offset, square, font=font, fill=fill)

        # text
        font = get_font(locale, 60, "Medium")
        fill = asset.primary_text if not dark_mode else asset.white
        draw.text((offset[0], offset[1] + 61), text, font=font, fill=fill)

        # small text
        if num == 3 or num == 4:
            font = get_font(locale, 30)
            fill = asset.secondary_text if not dark_mode else asset.white
            draw.text(
                (offset[0] + 110, offset[1] + 93),
                text_map.get(697 if num == 3 else 696, locale),
                font=font,
                fill=fill,
            )

        offset = (offset[0] + 486, offset[1])

    # expeditions
    font = get_font(locale, 55, "Bold")
    fill = asset.primary_text if not dark_mode else asset.white
    draw.text((79, 1029), text_map.get(20, locale), font=font, fill=fill)
    offset = (241, 1175)
    expeditions = note.expeditions
    for expedition in expeditions:
        character = expedition.character

        # name
        font = get_font(locale, 40, "Medium")
        fill = asset.primary_text if not dark_mode else asset.white
        draw.text(offset, character.name, font=font, fill=fill)

        # status
        font = get_font(locale, 25)
        fill = "#444444" if not dark_mode else asset.white
        status_text = text_map.get(
            694 if expedition.status == "Ongoing" else 695, locale
        )
        draw.text((offset[0], offset[1] + 60), status_text, font=font, fill=fill)

        # time
        font = get_font(locale, 40)
        fill = asset.primary_text if not dark_mode else asset.white
        if expedition.status == "Finished":
            time_text = text_map.get(695, locale)
        else:
            time_text = text_map.get(694, locale)

        draw.text(
            (offset[0] + 704 - font.getlength(time_text), offset[1] + 27),
            time_text,
            font=font,
            fill=fill,
        )

        # icon
        icon = get_cache(character.icon)
        icon = circular_crop(icon)
        icon = icon.resize((100, 100))
        im.paste(icon, (offset[0] - 131, offset[1] - 4), icon)

        offset = (offset[0], offset[1] + 199)

    fp = io.BytesIO()
    im = im.convert("RGB")
    im.save(fp, "JPEG", quality=95, optimize=True)
    return fp
