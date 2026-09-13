from PIL import Image
from pathlib import Path

src = Path(r"C:\Users\clove\.cursor\projects\c-Users-clove-CursorProjects-DSR-EventLab-Codes-Page\assets")
out = Path(r"C:\Users\clove\CursorProjects\DSR EventLab Codes Page\assets\brand")
out.mkdir(parents=True, exist_ok=True)


def autocrop_black(path_in: Path, path_out: Path, threshold: int = 18, pad: int = 24) -> None:
    im = Image.open(path_in).convert("RGB")
    w, h = im.size
    px = im.load()
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r > threshold or g > threshold or b > threshold:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x <= min_x or max_y <= min_y:
        im.save(path_out)
        print("no crop", path_in.name)
        return
    min_x = max(0, min_x - pad)
    min_y = max(0, min_y - pad)
    max_x = min(w - 1, max_x + pad)
    max_y = min(h - 1, max_y + pad)
    cropped = im.crop((min_x, min_y, max_x + 1, max_y + 1))
    cropped.save(path_out, optimize=True)
    print(path_in.name, "->", cropped.size, "saved", path_out.name)


autocrop_black(src / "title-eventlab-track-codes.png", out / "title-eventlab-track-codes.png")
autocrop_black(src / "title-time-attack.png", out / "title-time-attack.png")
autocrop_black(src / "wordmark-doomsantos-racing.png", out / "wordmark-doomsantos-racing.png", pad=16)
print("done")
