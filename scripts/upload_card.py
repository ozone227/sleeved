#!/usr/bin/env python3
"""
upload_card.py — Add a card photo to the Sleeved inventory

Processes a card photo, uploads it to S3, and updates the game's inventory.json.
Run from the repo root or scripts/ directory.

Usage:
    python scripts/upload_card.py --help
"""

import argparse
import json
import re
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    sys.exit("Missing dependency: pip install boto3")

try:
    from PIL import Image
except ImportError:
    sys.exit("Missing dependency: pip install Pillow")

try:
    import jsonschema
except ImportError:
    sys.exit("Missing dependency: pip install jsonschema")


# ── Config ─────────────────────────────────────────────────────────────────────

BUCKET = "sleeved-collection"
REGION = "us-east-1"
MAX_DIMENSION = 1200   # px — large enough for gallery zoom
IMAGE_QUALITY = 88     # JPEG quality (0–95)

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "schema" / "inventory.schema.json"
GAMES_DIR   = REPO_ROOT / "games"


# ── Helpers ────────────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """'Johnny Silverhand' → 'johnny-silverhand'"""
    s = name.lower().strip()
    s = re.sub(r"[''`]", "", s)        # drop apostrophes
    s = re.sub(r"[^a-z0-9]+", "-", s)  # non-alphanumeric → hyphen
    return s.strip("-")


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_game_config(game_id: str) -> dict:
    path = GAMES_DIR / f"{game_id}.json"
    if not path.exists():
        sys.exit(f"Game config not found: {path}\nSupported games: "
                 + ", ".join(p.stem for p in GAMES_DIR.glob("*.json")))
    return load_json(path)


def parse_ram(raw: str) -> dict:
    """Parse 'red:2,green:1' → {'red': 2, 'green': 1}"""
    result = {}
    for part in raw.split(","):
        color, sep, value = part.strip().partition(":")
        if not sep:
            sys.exit(f"Invalid --ram format near '{part}'. Expected 'color:N,...' e.g. 'red:2,green:1'")
        try:
            result[color.strip().lower()] = int(value.strip())
        except ValueError:
            sys.exit(f"RAM value for '{color}' must be an integer, got '{value}'")
    return result


def s3_key_for_card(card_type: str, color: str | None, card_id: str,
                     game_config: dict) -> str:
    """Return the full S3 key for a card image."""
    template = game_config["structure"]["s3Paths"][card_type]
    relative = template.replace("{color}", (color or "").lower())
    return f"{game_config['s3Prefix']}/{relative}/{card_id}.jpg"


def image_field(s3_key: str, game_config: dict) -> str:
    """Strip the game prefix from an S3 key to get the inventory image field."""
    prefix = game_config["s3Prefix"] + "/"
    return s3_key.removeprefix(prefix)


def process_image(path: Path) -> bytes:
    """Resize, convert to RGB, strip EXIF, and return JPEG bytes."""
    with Image.open(path) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=IMAGE_QUALITY, optimize=True)
        return buf.getvalue()


def fetch_inventory(s3_client, game_id: str) -> dict:
    key = f"{game_id}/inventory.json"
    try:
        resp = s3_client.get_object(Bucket=BUCKET, Key=key)
        return json.loads(resp["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            sys.exit(f"inventory.json not found at s3://{BUCKET}/{key}\n"
                     "Run scripts/setup-bucket.sh first.")
        raise


def push_inventory(s3_client, inventory: dict, game_id: str) -> None:
    key = f"{game_id}/inventory.json"
    body = json.dumps(inventory, indent=2, ensure_ascii=False).encode("utf-8")
    s3_client.put_object(Bucket=BUCKET, Key=key, Body=body,
                         ContentType="application/json")


# ── CLI ────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="upload_card.py",
        description="Add a card photo to the Sleeved inventory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  # Unit card
  python scripts/upload_card.py -i ~/Downloads/card.jpg \\
      --name "Rogue Amerascu" --type Unit --color Red \\
      --set "Welcome to Night City" --rarity Rare \\
      --cost 5 --power 8 --keywords "Adrenaline" --copies 1

  # Legend with Go Solo and RAM
  python scripts/upload_card.py -i ~/Downloads/legend.jpg \\
      --name "Johnny Silverhand" --type Legend \\
      --set "Welcome to Night City" --rarity Legendary \\
      --cost 4 --ram "red:3,blue:2" --keywords "Go Solo" --copies 1

  # Dry run — validate and preview without uploading
  python scripts/upload_card.py -i photo.jpg \\
      --name "Test Card" --type Unit --color Green \\
      --set "Welcome to Night City" --rarity Common \\
      --cost 1 --copies 1 --dry-run
        """,
    )

    req = p.add_argument_group("required")
    req.add_argument("-i", "--image",   required=True, help="Path to card photo")
    req.add_argument("--name",          required=True, help="Card name")
    req.add_argument("--type",          required=True,
                     choices=["Legend", "Unit", "Program", "Gear"])
    req.add_argument("--set",           required=True, dest="set_name",
                     help="Set name, e.g. 'Welcome to Night City'")
    req.add_argument("--rarity",        required=True,
                     help="Rarity, e.g. Common, Uncommon, Rare, Legendary")
    req.add_argument("--copies",        required=True, type=int, choices=[1, 2, 3],
                     help="Copies owned")

    opt = p.add_argument_group("card attributes")
    opt.add_argument("--color",    choices=["Red", "Green", "Blue", "Yellow"],
                     help="Color (required for Unit, Program, Gear)")
    opt.add_argument("--cost",     type=int,   default=None, help="Eddie cost to play")
    opt.add_argument("--power",    type=int,   default=None, help="Combat power")
    opt.add_argument("--ram",      default=None,
                     help="Legend RAM, e.g. 'red:2,green:1'")
    opt.add_argument("--keywords", default="",
                     help="Comma-separated keywords, e.g. 'Adrenaline,Blocker'")
    opt.add_argument("--sell-tag", action="store_true", help="Card has a Sell Tag")
    opt.add_argument("--notes",    default="",  help="Optional free-text notes")

    misc = p.add_argument_group("misc")
    misc.add_argument("--game",    default="cyberpunk-tcg",
                      help="Game ID (default: cyberpunk-tcg)")
    misc.add_argument("--id",      default=None, dest="card_id",
                      help="Override auto-generated slug")
    misc.add_argument("--dry-run", action="store_true",
                      help="Validate and preview without touching S3")

    return p


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ── Validate cross-field rules ─────────────────────────────────────────────
    if args.type != "Legend" and not args.color:
        parser.error(f"--color is required for card type '{args.type}'")
    if args.type == "Legend" and args.color:
        print(f"Note: Legends have no color — ignoring --color '{args.color}'.")
        args.color = None

    image_path = Path(args.image).expanduser().resolve()
    if not image_path.exists():
        sys.exit(f"Image not found: {image_path}")

    # ── Load config and schema ─────────────────────────────────────────────────
    game_config = load_game_config(args.game)
    schema = load_json(SCHEMA_PATH)

    # ── Build card entry ───────────────────────────────────────────────────────
    card_id = args.card_id or slugify(args.name)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    key = s3_key_for_card(args.type, args.color, card_id, game_config)

    card = {
        "id":       card_id,
        "name":     args.name,
        "type":     args.type,
        "color":    args.color,
        "set":      args.set_name,
        "rarity":   args.rarity,
        "cost":     args.cost,
        "power":    args.power,
        "ram":      parse_ram(args.ram) if args.ram else None,
        "keywords": keywords,
        "sellTag":  args.sell_tag,
        "copies":   args.copies,
        "image":    image_field(key, game_config),
        "notes":    args.notes,
    }

    # ── Validate against schema ────────────────────────────────────────────────
    card_schema = schema["properties"]["cards"]["items"]
    try:
        jsonschema.validate(instance=card, schema=card_schema)
    except jsonschema.ValidationError as e:
        sys.exit(f"Validation error: {e.message}")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n📋  Card entry:")
    print(json.dumps(card, indent=2))
    print(f"\n🖼   Image:  {image_path}")
    print(f"     S3 key: s3://{BUCKET}/{key}")

    if args.dry_run:
        print("\n[dry-run] No changes made.")
        return

    # ── Process image ──────────────────────────────────────────────────────────
    print("\n🔧  Processing image...")
    image_bytes = process_image(image_path)
    print(f"    {len(image_bytes) / 1024:.1f} KB (resized + EXIF stripped)")

    # ── S3 operations ──────────────────────────────────────────────────────────
    s3 = boto3.client("s3", region_name=REGION)

    # Check inventory for duplicate before uploading anything
    inventory = fetch_inventory(s3, args.game)
    existing = {c["id"] for c in inventory.get("cards", [])}
    if card_id in existing:
        print(f"\n⚠️  '{card_id}' already exists in inventory.")
        confirm = input("   Overwrite? [y/N] ").strip().lower()
        if confirm != "y":
            sys.exit("Aborted — no changes made.")
        inventory["cards"] = [c for c in inventory["cards"] if c["id"] != card_id]

    # Upload image
    print(f"\n⬆️  Uploading image...")
    try:
        s3.put_object(Bucket=BUCKET, Key=key, Body=image_bytes,
                      ContentType="image/jpeg")
        print(f"    ✅ https://{BUCKET}.s3.amazonaws.com/{key}")
    except ClientError as e:
        sys.exit(f"Image upload failed: {e}")

    # Update inventory (with rollback on failure)
    print(f"\n📝  Updating inventory.json...")
    try:
        inventory["cards"].append(card)
        inventory["lastUpdated"] = date.today().isoformat()
        push_inventory(s3, inventory, args.game)
        print(f"    ✅ {len(inventory['cards'])} card(s) in collection")
    except Exception as e:
        print(f"    ❌ Failed: {e}")
        print("    🔄 Rolling back — removing uploaded image...")
        s3.delete_object(Bucket=BUCKET, Key=key)
        sys.exit("Rolled back. No changes made.")

    print(f"\n🎉  '{args.name}' added to your {args.game} collection.")
    print(f"    https://{BUCKET}.s3.amazonaws.com/{key}")


if __name__ == "__main__":
    main()
