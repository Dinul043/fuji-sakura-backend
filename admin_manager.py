#!/usr/bin/env python3
"""
Admin Management Tool for Fuji Sakura Food Delivery
Usage: python admin_manager.py [command] [options]

Commands:
  add <name> <email> <password>     - Add new admin
  add-super <name> <email> <password> - Add new super admin
  list                              - List all admins
  activate <email>                  - Activate admin
  deactivate <email>                - Deactivate admin
  make-super <email>                - Make admin a super admin
  remove-super <email>              - Remove super admin privileges
  delete <email>                    - Delete admin (permanent)
  change-password <email> <new_password> - Change admin password
"""

import sys
import os
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.utils.security import get_password_hash, verify_password
from app.models.admin import Admin
from sqlalchemy.orm import Session

def print_usage():
    """Print usage instructions"""
    print(__doc__)

def add_admin(name: str, email: str, password: str, is_super: bool = False):
    """Add a new admin"""
    try:
        db = next(get_db())
        
        # Check if admin already exists
        existing_admin = db.query(Admin).filter(Admin.email == email).first()
        if existing_admin:
            print(f"❌ Error: Admin with email '{email}' already exists!")
            return False
        
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Create new admin
        new_admin = Admin(
            name=name,
            email=email,
            password=hashed_password,
            is_active=True,
            is_super_admin=is_super,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        
        admin_type = "Super Admin" if is_super else "Admin"
        print(f"✅ {admin_type} added successfully!")
        print(f"   ID: {new_admin.id}")
        print(f"   Name: {new_admin.name}")
        print(f"   Email: {new_admin.email}")
        print(f"   Type: {'Super Admin' if new_admin.is_super_admin else 'Regular Admin'}")
        print(f"   Status: {'Active' if new_admin.is_active else 'Inactive'}")
        print(f"   Created: {new_admin.created_at}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding admin: {e}")
        return False
    finally:
        db.close()

def list_admins():
    """List all admins"""
    try:
        db = next(get_db())
        
        admins = db.query(Admin).order_by(Admin.id).all()
        
        if not admins:
            print("📭 No admins found in the database.")
            return
        
        print(f"👥 Found {len(admins)} admin(s):")
        print("-" * 90)
        print(f"{'ID':<4} {'Name':<20} {'Email':<30} {'Type':<12} {'Status':<10} {'Created':<20}")
        print("-" * 90)
        
        for admin in admins:
            admin_type = "Super Admin" if admin.is_super_admin else "Regular"
            status = "Active" if admin.is_active else "Inactive"
            created = admin.created_at.strftime("%Y-%m-%d %H:%M") if admin.created_at else "N/A"
            print(f"{admin.id:<4} {admin.name:<20} {admin.email:<30} {admin_type:<12} {status:<10} {created:<20}")
        
        print("-" * 90)
        
    except Exception as e:
        print(f"❌ Error listing admins: {e}")
    finally:
        db.close()

def activate_admin(email: str):
    """Activate an admin"""
    try:
        db = next(get_db())
        
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            print(f"❌ Error: Admin with email '{email}' not found!")
            return False
        
        if admin.is_active:
            print(f"ℹ️  Admin '{email}' is already active.")
            return True
        
        admin.is_active = True
        admin.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
        print(f"✅ Admin '{email}' activated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error activating admin: {e}")
        return False
    finally:
        db.close()

def deactivate_admin(email: str):
    """Deactivate an admin"""
    try:
        db = next(get_db())
        
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            print(f"❌ Error: Admin with email '{email}' not found!")
            return False
        
        if not admin.is_active:
            print(f"ℹ️  Admin '{email}' is already inactive.")
            return True
        
        admin.is_active = False
        admin.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
        print(f"✅ Admin '{email}' deactivated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error deactivating admin: {e}")
        return False
    finally:
        db.close()

def delete_admin(email: str):
    """Delete an admin permanently"""
    try:
        db = next(get_db())
        
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            print(f"❌ Error: Admin with email '{email}' not found!")
            return False
        
        # Confirm deletion
        print(f"⚠️  WARNING: This will permanently delete admin '{admin.name}' ({email})")
        confirm = input("Type 'DELETE' to confirm: ")
        
        if confirm != 'DELETE':
            print("❌ Deletion cancelled.")
            return False
        
        db.delete(admin)
        db.commit()
        
        print(f"✅ Admin '{email}' deleted permanently!")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting admin: {e}")
        return False
    finally:
        db.close()

def change_password(email: str, new_password: str):
    """Change admin password"""
    try:
        db = next(get_db())
        
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            print(f"❌ Error: Admin with email '{email}' not found!")
            return False
        
        # Hash the new password
        hashed_password = get_password_hash(new_password)
        
        admin.password = hashed_password
        admin.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
        print(f"✅ Password changed successfully for admin '{email}'!")
        return True
        
    except Exception as e:
        print(f"❌ Error changing password: {e}")
        return False
    finally:
        db.close()

def make_super_admin(email: str):
    """Make an admin a super admin"""
    try:
        db = next(get_db())
        
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            print(f"❌ Error: Admin with email '{email}' not found!")
            return False
        
        if admin.is_super_admin:
            print(f"ℹ️  Admin '{email}' is already a super admin.")
            return True
        
        admin.is_super_admin = True
        admin.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
        print(f"✅ Admin '{email}' is now a Super Admin!")
        print(f"   🔥 Super Admin privileges granted!")
        return True
        
    except Exception as e:
        print(f"❌ Error making super admin: {e}")
        return False
    finally:
        db.close()

def remove_super_admin(email: str):
    """Remove super admin privileges"""
    try:
        db = next(get_db())
        
        admin = db.query(Admin).filter(Admin.email == email).first()
        if not admin:
            print(f"❌ Error: Admin with email '{email}' not found!")
            return False
        
        if not admin.is_super_admin:
            print(f"ℹ️  Admin '{email}' is not a super admin.")
            return True
        
        admin.is_super_admin = False
        admin.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
        print(f"✅ Super admin privileges removed from '{email}'!")
        print(f"   👤 Now a regular admin.")
        return True
        
    except Exception as e:
        print(f"❌ Error removing super admin: {e}")
        return False
    finally:
        db.close()

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "add":
        if len(sys.argv) != 5:
            print("❌ Usage: python admin_manager.py add <name> <email> <password>")
            print("   Example: python admin_manager.py add \"John Doe\" john@company.com mypassword123")
            return
        
        name = sys.argv[2]
        email = sys.argv[3]
        password = sys.argv[4]
        add_admin(name, email, password, is_super=False)
    
    elif command == "add-super":
        if len(sys.argv) != 5:
            print("❌ Usage: python admin_manager.py add-super <name> <email> <password>")
            print("   Example: python admin_manager.py add-super \"Super Admin\" super@company.com mypassword123")
            return
        
        name = sys.argv[2]
        email = sys.argv[3]
        password = sys.argv[4]
        add_admin(name, email, password, is_super=True)
    
    elif command == "list":
        list_admins()
    
    elif command == "activate":
        if len(sys.argv) != 3:
            print("❌ Usage: python admin_manager.py activate <email>")
            return
        
        email = sys.argv[2]
        activate_admin(email)
    
    elif command == "deactivate":
        if len(sys.argv) != 3:
            print("❌ Usage: python admin_manager.py deactivate <email>")
            return
        
        email = sys.argv[2]
        deactivate_admin(email)
    
    elif command == "make-super":
        if len(sys.argv) != 3:
            print("❌ Usage: python admin_manager.py make-super <email>")
            return
        
        email = sys.argv[2]
        make_super_admin(email)
    
    elif command == "remove-super":
        if len(sys.argv) != 3:
            print("❌ Usage: python admin_manager.py remove-super <email>")
            return
        
        email = sys.argv[2]
        remove_super_admin(email)
    
    elif command == "delete":
        if len(sys.argv) != 3:
            print("❌ Usage: python admin_manager.py delete <email>")
            return
        
        email = sys.argv[2]
        delete_admin(email)
    
    elif command == "change-password":
        if len(sys.argv) != 4:
            print("❌ Usage: python admin_manager.py change-password <email> <new_password>")
            return
        
        email = sys.argv[2]
        new_password = sys.argv[3]
        change_password(email, new_password)
    
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()

if __name__ == "__main__":
    main()