
# -*- coding: utf-8 -*-
import pygame
import random
import math
import time
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image

# ==================== Settings ====================

WIDTH, HEIGHT = 1200, 800
BG = (29, 32, 41)
PANEL = (43, 47, 59)
WHITE = (245, 246, 250)
GREEN = (91, 205, 145)
MUTED = (177, 184, 198)
TRAY = (36, 40, 51)

pygame.init()
pygame.display.set_caption("Photo Puzzle")

screen = pygame.display.set_mode(
    (WIDTH, HEIGHT), pygame.RESIZABLE
)
clock = pygame.time.Clock()

font = pygame.font.SysFont("arial", 20)
small_font = pygame.font.SysFont("arial", 15)
title_font = pygame.font.SysFont("arial", 28, bold=True)
button_font = pygame.font.SysFont("arial", 16, bold=True)

# ==================== Select Photo ====================

root = tk.Tk()
root.withdraw()

image_path = filedialog.askopenfilename(
    title="Choose a photo for your puzzle",
    filetypes=[
        ("Image files", "*.jpg *.jpeg *.png *.bmp *.webp")
    ]
)

if not image_path:
    root.destroy()
    pygame.quit()
    raise SystemExit

# Select difficulty
dialog = tk.Toplevel(root)
dialog.title("Choose Difficulty")
dialog.geometry("340x285")
dialog.resizable(False, False)
dialog.grab_set()

tk.Label(
    dialog,
    text="Choose your difficulty level",
    font=("Arial", 12, "bold")
).pack(pady=12)

difficulty_var = tk.StringVar(value="Medium")

for name, description in [
    ("Easy", "10 pieces"),
    ("Medium", "30 pieces"),
    ("Hard", "50 pieces"),
    ("Expert", "100 pieces"),
    ("Custom", "Choose your own number"),
]:
    tk.Radiobutton(
        dialog,
        text=f"{name} - {description}",
        variable=difficulty_var,
        value=name,
        anchor="w"
    ).pack(fill="x", padx=35)

tk.Button(
    dialog,
    text="Start Game",
    command=dialog.destroy
).pack(pady=12)

root.wait_window(dialog)
difficulty = difficulty_var.get()

presets = {
    "Easy": 10,
    "Medium": 30,
    "Hard": 50,
    "Expert": 100,
}

if difficulty == "Custom":
    count_1 = simpledialog.askinteger(
        "Puzzle Size",
        "How many pieces? (2 to 100)",
        initialvalue=100,
        minvalue=2,
        maxvalue=100,
        parent=root
    )
    count= int(count_1//2)*2
else:
    count = presets[difficulty]

root.destroy()

if not count:
    pygame.quit()
    raise SystemExit

try:
    original = Image.open(image_path).convert("RGB")
except Exception as error:
    messagebox.showerror("Image Error", str(error))
    pygame.quit()
    raise SystemExit

image_ratio = original.width / original.height

# ==================== Calculate Grid ====================

def calculate_grid(number, ratio):
    """Find a grid with exactly the requested number of pieces."""
    best = None

    for cols in range(1, number + 1):
        if number % cols == 0:
            rows = number // cols
            score = abs(math.log((cols / rows) / ratio))

            if best is None or score < best[0]:
                best = (score, cols, rows)

        if cols > math.sqrt(number) * 2 and best:
            break

    return best[1], best[2]


columns, rows = calculate_grid(count, image_ratio)

pieces = []
dragging = None
drag_offset = (0, 0)
show_preview = False
show_grid = True
start_time = time.monotonic()
won_time = None
piece_margin = 12
board = pygame.Rect(25, 125, 700, 500)


# ==================== Puzzle Piece Shapes ====================

def edge_points(start, end, normal, sign, depth):
    """Create an edge with a tab or indentation."""

    fractions = [
        0.0, 0.28, 0.36, 0.40, 0.44,
        0.50, 0.56, 0.60, 0.64, 0.72, 1.0
    ]

    profile = [
        0, 0, 0.18, 0.72, 1.0,
        1.0, 1.0, 0.72, 0.18, 0, 0
    ]

    points = []

    for fraction, height in zip(fractions, profile):
        x = start[0] + (end[0] - start[0]) * fraction
        y = start[1] + (end[1] - start[1]) * fraction

        offset = sign * depth * height

        points.append((
            round(x + normal[0] * offset),
            round(y + normal[1] * offset)
        ))

    return points


def make_outline(w, h, margin, top, right, bottom, left, depth):
    """Create the piece outline clockwise."""

    x0, y0 = margin, margin
    x1, y1 = margin + w, margin + h

    points = []

    points += edge_points(
        (x0, y0), (x1, y0), (0, -1), top, depth
    )

    points += edge_points(
        (x1, y0), (x1, y1), (1, 0), right, depth
    )[1:]

    points += edge_points(
        (x1, y1), (x0, y1), (0, 1), bottom, depth
    )[1:]

    points += edge_points(
        (x0, y1), (x0, y0), (-1, 0), left, depth
    )[1:]

    return points


# ==================== Create Puzzle ====================

def create_puzzle():
    global pieces, board, piece_margin, won_time, dragging

    pieces = []
    won_time = None
    dragging = None

    window_w, window_h = screen.get_size()

    available_w = max(220, window_w - 365)
    available_h = max(220, window_h - 165)

    board_w = min(available_w, available_h * image_ratio)
    board_h = board_w / image_ratio

    if board_h > available_h:
        board_h = available_h
        board_w = board_h * image_ratio

    board = pygame.Rect(
        24, 125, int(board_w), int(board_h)
    )

    cell_w = board.width / columns
    cell_h = board.height / rows

    piece_margin = max(
        3, min(20, int(min(cell_w, cell_h) * 0.24))
    )
    depth = piece_margin * 0.82

    # Scale the image and add a border for puzzle tabs.
    scaled = pygame.image.fromstring(
        original.resize(
            board.size, Image.Resampling.LANCZOS
        ).tobytes(),
        board.size,
        "RGB"
    )

    padded = pygame.Surface(
        (
            board.width + 2 * piece_margin,
            board.height + 2 * piece_margin
        ),
        pygame.SRCALPHA
    )

    padded.fill((0, 0, 0, 0))
    padded.blit(scaled, (piece_margin, piece_margin))

    # Generate shared edges so neighboring pieces match.
    horizontal_edges = [
        [random.choice((-1, 1)) for _ in range(columns)]
        for _ in range(rows - 1)
    ]

    vertical_edges = [
        [random.choice((-1, 1)) for _ in range(columns - 1)]
        for _ in range(rows)
    ]

    for row in range(rows):
        for col in range(columns):

            x0 = round(col * cell_w)
            x1 = round((col + 1) * cell_w)
            y0 = round(row * cell_h)
            y1 = round((row + 1) * cell_h)

            tile_w = x1 - x0
            tile_h = y1 - y0

            target = pygame.Rect(
                board.x + x0 - piece_margin,
                board.y + y0 - piece_margin,
                tile_w + 2 * piece_margin,
                tile_h + 2 * piece_margin
            )

            # Outer edges are flat.
            top = (
                0 if row == 0
                else -horizontal_edges[row - 1][col]
            )

            bottom = (
                0 if row == rows - 1
                else horizontal_edges[row][col]
            )

            left = (
                0 if col == 0
                else -vertical_edges[row][col - 1]
            )

            right = (
                0 if col == columns - 1
                else vertical_edges[row][col]
            )

            outline = make_outline(
                tile_w, tile_h, piece_margin,
                top, right, bottom, left, depth
            )

            # Extract the image section, including the tab margins.
            crop_rect = pygame.Rect(
                x0, y0,
                tile_w + 2 * piece_margin,
                tile_h + 2 * piece_margin
            )

            surface = padded.subsurface(crop_rect).copy()

            # Apply a transparent mask in the puzzle piece shape.
            mask_surface = pygame.Surface(
                surface.get_size(), pygame.SRCALPHA
            )

            pygame.draw.polygon(
                mask_surface,
                (255, 255, 255, 255),
                outline
            )

            surface.blit(
                mask_surface,
                (0, 0),
                special_flags=pygame.BLEND_RGBA_MULT
            )

            pieces.append({
                "surface": surface,
                "target": target,
                "rect": target.copy(),
                "placed": False,
                "index": row * columns + col,
            })

    # Shuffle pieces and distribute them in the tray.
    tray_x = board.right + 24
    tray_w = max(100, window_w - tray_x - 16)

    order = list(range(len(pieces)))
    random.shuffle(order)

    tray_cols = max(1, min(10, int(tray_w / 55)))
    tray_rows = math.ceil(len(order) / tray_cols)

    slot_w = tray_w / tray_cols
    slot_h = board.height / tray_rows

    for position, index in enumerate(order):
        piece = pieces[index]

        col = position % tray_cols
        row = position // tray_cols

        surface = piece["surface"]

        max_w = max(7, int(slot_w - 3))
        max_h = max(7, int(slot_h - 3))

        scale = min(
            max_w / surface.get_width(),
            max_h / surface.get_height(),
            1.0
        )

        size = (
            max(1, int(surface.get_width() * scale)),
            max(1, int(surface.get_height() * scale))
        )

        piece["tray_surface"] = pygame.transform.smoothscale(
            surface, size
        )

        piece["rect"] = pygame.Rect(
            int(tray_x + col * slot_w + (slot_w - size[0]) / 2),
            int(board.y + row * slot_h + (slot_h - size[1]) / 2),
            *size
        )
        piece["tray_rect"] = piece["rect"].copy()


# ==================== Game Controls ====================

def reset_game():
    global start_time, show_preview

    start_time = time.monotonic()
    show_preview = False
    create_puzzle()


def format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def draw_button(rect, label, active=False):
    color = GREEN if active else (65, 72, 88)

    pygame.draw.rect(
        screen, color, rect, border_radius=7
    )

    text = button_font.render(
        label,
        True,
        (20, 25, 30) if active else WHITE
    )

    screen.blit(text, text.get_rect(center=rect.center))


# ==================== Draw Placement Grid ====================

def draw_grid():
    """Draw guide lines matching the puzzle piece layout."""
    if not show_grid:
        return

    grid_color = (105, 112, 128)

    # Vertical lines between puzzle columns.
    for col in range(columns + 1):
        x = round(board.x + col * board.width / columns)

        pygame.draw.line(
            screen,
            grid_color,
            (x, board.y),
            (x, board.bottom),
            1
        )

    # Horizontal lines between puzzle rows.
    for row in range(rows + 1):
        y = round(board.y + row * board.height / rows)

        pygame.draw.line(
            screen,
            grid_color,
            (board.x, y),
            (board.right, y),
            1
        )

    pygame.draw.rect(screen, (145, 152, 168), board, 1)


# ==================== Main Game Loop ====================

create_puzzle()
running = True

while running:
    clock.tick(60)

    window_w, window_h = screen.get_size()

    completed = sum(
        1 for piece in pieces if piece["placed"]
    )

    now = won_time if won_time is not None else time.monotonic()
    elapsed = now - start_time

    preview_button = pygame.Rect(
        max(550, window_w - 300), 18, 112, 34
    )

    restart_button = pygame.Rect(
        max(670, window_w - 174), 18, 125, 34
    )

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode(
                event.size, pygame.RESIZABLE
            )
            create_puzzle()

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_r:
                reset_game()

            elif event.key == pygame.K_p:
                show_preview = not show_preview

            elif event.key == pygame.K_g:
                show_grid = not show_grid

            elif event.key == pygame.K_ESCAPE:
                show_preview = False

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):

            if preview_button.collidepoint(event.pos):
                show_preview = not show_preview
                continue

            if restart_button.collidepoint(event.pos):
                reset_game()
                continue

            if show_preview:
                show_preview = False
                continue

            # Select the topmost unplaced piece.
            for piece in reversed(pieces):

                if (
                    not piece["placed"]
                    and piece["rect"].collidepoint(event.pos)
                ):
                    dragging = piece

                    drag_offset = (
                        piece["rect"].x - event.pos[0],
                        piece["rect"].y - event.pos[1]
                    )

                    pieces.remove(piece)
                    pieces.append(piece)
                    break

        elif (
            event.type == pygame.MOUSEMOTION
            and dragging is not None
        ):

            dragging["rect"].x = (
                event.pos[0] + drag_offset[0]
            )

            dragging["rect"].y = (
                event.pos[1] + drag_offset[1]
            )

        
        elif (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and dragging is not None
        ):

            piece = dragging
            target = piece["target"]

            # Check whether the piece is close enough to snap.
            dx = abs(piece["rect"].centerx - target.centerx)
            dy = abs(piece["rect"].centery - target.centery)

            cell_w = board.width / columns
            cell_h = board.height / rows

            # More forgiving placement tolerance.
            tolerance_x = max(16, cell_w * 0.55)
            tolerance_y = max(16, cell_h * 0.55)

            if dx < tolerance_x and dy < tolerance_y:
                # Snap the piece exactly into place.
                piece["rect"] = target.copy()
                piece["placed"] = True

                if all(p["placed"] for p in pieces):
                    won_time = time.monotonic()

            else:
                # Return only this piece to the tray.
                piece["rect"] = piece["tray_rect"].copy()

            dragging = None


    # ==================== Draw Interface ====================

    screen.fill(BG)

    pygame.draw.rect(
        screen, PANEL, (0, 0, window_w, 105)
    )

    screen.blit(
        title_font.render("Photo Puzzle", True, WHITE),
        (24, 10)
    )

    screen.blit(
        font.render(
            f"{difficulty} | {count} pieces",
            True, GREEN
        ),
        (25, 53)
    )

    screen.blit(
        small_font.render(
            f"Progress: {completed}/{count}",
            True, WHITE
        ),
        (260, 20)
    )

    screen.blit(
        small_font.render(
            f"Time: {format_time(elapsed)}",
            True, WHITE
        ),
        (260, 48)
    )

    screen.blit(
        small_font.render(
            "G: Grid | P: Preview | R: Restart",
            True, MUTED
        ),
        (390, 73)
    )

    draw_button(
        preview_button, "Preview (P)", show_preview
    )

    draw_button(restart_button, "Restart (R)")

    # Draw the board background.
    pygame.draw.rect(
        screen, (49, 53, 65), board, border_radius=4
    )

    # Draw grid lines before the pieces so placed pieces cover them.
    draw_grid()

    # Draw the piece tray.
    tray_x = board.right + 15

    pygame.draw.rect(
        screen,
        TRAY,
        (
            tray_x, board.y,
            max(1, window_w - tray_x - 12),
            board.height
        ),
        border_radius=8
    )

    screen.blit(
        small_font.render("Piece Tray", True, MUTED),
        (tray_x + 8, board.y + 5)
    )

    # Display the original image as a preview.
    if show_preview:
        preview = pygame.image.fromstring(
            original.resize(
                board.size, Image.Resampling.LANCZOS
            ).tobytes(),
            board.size,
            "RGB"
        )

        preview.set_alpha(235)
        screen.blit(preview, board.topleft)

        pygame.draw.rect(screen, WHITE, board, 2)

        hint = small_font.render(
            "Preview - press P or click to close",
            True, WHITE
        )

        screen.blit(
            hint,
            (board.x + 8, board.bottom + 5)
        )

    # Draw completed pieces first.
    for piece in pieces:
        if piece["placed"]:
            screen.blit(
                piece["surface"], piece["rect"]
            )

    # Draw loose pieces on top.
    for piece in pieces:
        if not piece["placed"]:

            surface = (
                piece["surface"]
                if piece is dragging
                else piece["tray_surface"]
            )

            screen.blit(surface, piece["rect"])

    # Victory screen.
    if completed == count:

        overlay = pygame.Surface(
            (window_w, window_h), pygame.SRCALPHA
        )

        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        title = title_font.render(
            "Congratulations! Puzzle solved!",
            True, GREEN
        )

        subtitle = font.render(
            f"Your time: {format_time(elapsed)}",
            True, WHITE
        )

        screen.blit(
            title,
            title.get_rect(
                center=(window_w // 2, window_h // 2 - 20)
            )
        )

        screen.blit(
            subtitle,
            subtitle.get_rect(
                center=(window_w // 2, window_h // 2 + 20)
            )
        )

    pygame.display.flip()

pygame.quit()
