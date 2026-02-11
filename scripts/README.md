# Utility Scripts

This folder contains utility and migration scripts for the backend.

## Migration Scripts (One-time use)

These scripts were used to add columns to the database. They've already been run and are kept for reference:

- `add_is_online_column.py` - Added `is_online` column to restaurants
- `add_is_veg_to_menu.py` - Added `is_veg` column to menu items

## Debug/Check Scripts

These scripts help verify database state:

- `check_is_veg_column.py` - Verify `is_veg` column exists and check sample data
- `check_menu_item.py` - Check specific menu item details

## Usage

Run from the backend root directory:

```bash
cd food-delivery-backend
python scripts/check_is_veg_column.py
```
