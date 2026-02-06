"""
File cleanup utilities for managing uploaded images
"""
import os
from pathlib import Path
from typing import Optional

def delete_old_image(image_url: Optional[str], image_type: str = "restaurant") -> bool:
    """
    Delete old image file from uploads directory
    
    Args:
        image_url: Full URL of the image to delete
        image_type: Type of image ("restaurant" or "menu")
    
    Returns:
        bool: True if deletion was successful or no file to delete, False if error
    """
    if not image_url:
        return True
    
    try:
        # Determine the upload directory based on image type
        if image_type == "restaurant":
            upload_path = "uploads/restaurant_images/"
        elif image_type == "menu":
            upload_path = "uploads/menu_images/"
        else:
            print(f"Warning: Unknown image type '{image_type}'")
            return False
        
        # Extract filename from URL
        if upload_path in image_url:
            filename = image_url.split(upload_path)[-1]
            file_path = Path(upload_path) / filename
            
            if file_path.exists():
                file_path.unlink()  # Delete the file
                print(f"✅ Deleted old {image_type} image: {filename}")
                return True
            else:
                print(f"ℹ️ Old {image_type} image not found: {filename}")
                return True
        else:
            print(f"ℹ️ Image URL doesn't match expected pattern: {image_url}")
            return True
            
    except Exception as e:
        print(f"⚠️ Warning: Could not delete old {image_type} image: {e}")
        return False

def cleanup_restaurant_images(restaurant_id: int, keep_latest: int = 1) -> int:
    """
    Clean up old restaurant images, keeping only the latest N files
    
    Args:
        restaurant_id: ID of the restaurant
        keep_latest: Number of latest images to keep (default: 1)
    
    Returns:
        int: Number of files deleted
    """
    try:
        upload_dir = Path("uploads/restaurant_images")
        if not upload_dir.exists():
            return 0
        
        # Find all files for this restaurant
        pattern = f"restaurant_{restaurant_id}_*.png"
        restaurant_files = list(upload_dir.glob(pattern))
        restaurant_files.extend(list(upload_dir.glob(f"restaurant_{restaurant_id}_*.jpg")))
        restaurant_files.extend(list(upload_dir.glob(f"restaurant_{restaurant_id}_*.jpeg")))
        restaurant_files.extend(list(upload_dir.glob(f"restaurant_{restaurant_id}_*.webp")))
        
        if len(restaurant_files) <= keep_latest:
            return 0
        
        # Sort by modification time (newest first)
        restaurant_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Delete old files (keep only the latest N)
        deleted_count = 0
        for old_file in restaurant_files[keep_latest:]:
            try:
                old_file.unlink()
                print(f"🧹 Cleaned up old restaurant image: {old_file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete {old_file.name}: {e}")
        
        return deleted_count
        
    except Exception as e:
        print(f"⚠️ Error during restaurant image cleanup: {e}")
        return 0

def cleanup_menu_images(restaurant_id: int, menu_item_id: Optional[int] = None) -> int:
    """
    Clean up old menu images for a restaurant or specific menu item
    
    Args:
        restaurant_id: ID of the restaurant
        menu_item_id: Specific menu item ID (optional)
    
    Returns:
        int: Number of files deleted
    """
    try:
        upload_dir = Path("uploads/menu_images")
        if not upload_dir.exists():
            return 0
        
        # Find files to clean up
        if menu_item_id:
            # Clean up specific menu item images
            pattern = f"menu_{menu_item_id}_*.png"
            files_to_check = list(upload_dir.glob(pattern))
            files_to_check.extend(list(upload_dir.glob(f"menu_{menu_item_id}_*.jpg")))
            files_to_check.extend(list(upload_dir.glob(f"menu_{menu_item_id}_*.jpeg")))
            files_to_check.extend(list(upload_dir.glob(f"menu_{menu_item_id}_*.webp")))
        else:
            # This would require database query to find all menu items for restaurant
            # For now, just return 0
            return 0
        
        deleted_count = 0
        for old_file in files_to_check:
            try:
                old_file.unlink()
                print(f"🧹 Cleaned up old menu image: {old_file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"⚠️ Could not delete {old_file.name}: {e}")
        
        return deleted_count
        
    except Exception as e:
        print(f"⚠️ Error during menu image cleanup: {e}")
        return 0