#!/usr/bin/env python3
import json
import argparse
import os

def update_product_serial(gtin, last_serial):
    """Update the last serial number for a product in the database"""
    
    db_path = 'product_db.json'
    
    # Read current database
    with open(db_path, 'r') as f:
        data = json.load(f)
    
    # Find and update product
    updated = False
    for product in data['products']:
        if product['gtin'] == gtin:
            product['lastSerial'] = last_serial
            updated = True
            print(f"✓ Updated {product['name']} - Last Serial: {last_serial}")
            break
    
    if not updated:
        print(f"⚠ Warning: Product with GTIN {gtin} not found")
        return
    
    # Write back to database
    with open(db_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Database updated successfully")

def main():
    parser = argparse.ArgumentParser(description='Update product serial number')
    parser.add_argument('--gtin', required=True, help='Product GTIN')
    parser.add_argument('--last-serial', type=int, required=True, help='Last used serial number')
    
    args = parser.parse_args()
    
    update_product_serial(args.gtin, args.last_serial)

if __name__ == '__main__':
    main()
