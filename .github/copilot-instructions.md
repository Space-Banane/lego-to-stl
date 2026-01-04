# LEGO Set to STL Converter - AI Coding Instructions

## Project Architecture

This Flask web application converts LEGO sets to 3D-printable STL files by orchestrating three core modules:

1. **rebrickable.py** - Fetches set metadata and parts lists from Rebrickable API (requires `REBRICKABLE_API_KEY` env var)
2. **metadata.py** - Creates `.set.json` files with color-mapped parts data using `colors.csv` lookup
3. **converter.py** - Wraps `ldraw2stl/bin/dat2stl` Perl tool to convert LDraw `.dat` files to STL

### Data Flow
```
User Input (set_number) → rebrickable.py (API) → metadata.py (.set.json) → converter.py (Perl subprocess) → STL files
```

### Directory Structure
- `sets/<set_number>/` - Output directory containing `.set.json` metadata and `stls/` subdirectory
- `ldraw/parts/` - LDraw part library (`.dat` files)
- `ldraw2stl/bin/dat2stl` - Perl conversion tool (requires Perl/Strawberry Perl on Windows)

## Critical Dependencies

### External Tools
- **Perl** is REQUIRED for STL conversion (Strawberry Perl on Windows)
- All subprocess calls in `converter.py` invoke `perl ldraw2stl/bin/dat2stl`
- LDraw library must exist at `ldraw/` with `parts/` subdirectory

### API Requirements
- Rebrickable API key must be set via `.env` file or `REBRICKABLE_API_KEY` environment variable
- API client in `rebrickable.py` handles pagination automatically (default 1000 items/page)

## Development Workflows

### Running the Server
```powershell
python app.py
# Server starts at http://127.0.0.1:5000
```

### Testing Individual Modules
Each module has a `if __name__ == "__main__"` test block:
```powershell
python rebrickable.py    # Tests API connectivity
python converter.py      # Tests part conversion (outputs to test_output/)
python metadata.py       # Tests color mapping
```

### Processing Flow
Background thread in `app.py:process_set_background()` coordinates:
1. Fetch from Rebrickable (10% progress)
2. Create metadata (30% progress)
3. Convert parts to STL (50-100% progress)

Status tracked in global `processing_status` dict keyed by set_number.

## Code Conventions

### Error Handling Pattern
- Functions return `None` or `False` on failure (not exceptions)
- Example: `rebrickable.py:get_set_metadata()` returns `None` if set not found (404)
- Always check return values before proceeding

### Color ID Mapping
- `metadata.py` loads `colors.csv` at initialization into `self.colors_map` dict
- Color IDs from API are strings: `color_id = str(color_obj.get('id', ''))`
- Missing colors logged but don't block processing

### Part Number Handling
- Part numbers stored without `.dat` extension in metadata
- `converter.py:part_exists()` checks both original case and lowercase filenames
- Output STL files named `{part_num}.stl` in `sets/{set_number}/stls/`

## API Integration

### Rebrickable API v3 Format
Parts list returns nested structure:
```python
{
  "part": {"part_num": "3024", ...},
  "color": {"id": 0, "name": "Black", ...},
  "quantity": 4,
  "is_spare": false
}
```

Extract with: `part_obj.get('part', {})`, `color_obj.get('color', {})`

### Set Number Format
- API expects format: `"10245-1"` (set number + variant)
- UI accepts: `"10245"` (app adds `-1` suffix if needed)

## Common Pitfalls

1. **Subprocess Stdout Handling**: `converter.py` writes STL to stdout, captured via `stdout=subprocess.PIPE` then written to file
2. **Threading**: Flask endpoints spawn background threads for long processing - never block main thread
3. **Caching**: `skip_existing=True` in `convert_set()` prevents re-converting existing STLs
4. **Unique Parts**: Sets may have duplicate part+color combos - `convert_set()` deduplicates before conversion
5. **Windows Paths**: All file operations use `os.path.join()` for cross-platform compatibility

## Key Files Reference

- [app.py](app.py) - Flask routes, background processing orchestration
- [rebrickable.py](rebrickable.py) - `RebrickableClient` class with API methods
- [converter.py](converter.py) - `STLConverter` class wrapping Perl tool
- [metadata.py](metadata.py) - `MetadataHandler` for `.set.json` creation
- [notes.md](notes.md) - Original design doc with workflow explanation
- [colors.csv](colors.csv) - Color database (id, name, rgb, is_trans)

## Adding New Features

When extending conversion logic:
- Update `processing_status` dict for progress tracking
- Follow return `None`/`False` pattern instead of raising exceptions
- Add file I/O through existing `MetadataHandler` or `STLConverter` classes
- Test subprocess changes on both Windows and Unix paths
