#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
簡易版本測試腳本
用於驗證標註軟體的基本功能
"""

import sys
import os
from pathlib import Path

def check_test_data():
    """檢查測試資料是否完整"""
    current_dir = Path(__file__).parent
    test_dir = current_dir / "test"
    
    print("檢查測試資料...")
    
    # 檢查 test 資料夾
    if not test_dir.exists():
        print("❌ 找不到 test 資料夾")
        return False
    print("✅ test 資料夾存在")
    
    # 檢查 label.txt
    label_file = test_dir / "label.txt"
    if not label_file.exists():
        print("❌ 找不到 test/label.txt")
        return False
    print("✅ label.txt 存在")
    
    # 讀取類別
    with open(label_file, 'r', encoding='utf-8') as f:
        categories = [line.strip() for line in f if line.strip()]
    print(f"✅ 類別數量: {len(categories)} ({', '.join(categories)})")
    
    # 檢查 img 資料夾
    img_dir = test_dir / "img"
    if not img_dir.exists():
        print("❌ 找不到 test/img 資料夾")
        return False
    print("✅ img 資料夾存在")
    
    # 檢查圖片檔案
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    image_files = []
    for ext in image_extensions:
        image_files.extend(img_dir.glob(f"*{ext}"))
        image_files.extend(img_dir.glob(f"*{ext.upper()}"))
    
    print(f"✅ 圖片數量: {len(image_files)}")
    for img in sorted(image_files)[:5]:  # 只顯示前5個
        print(f"   - {img.name}")
    if len(image_files) > 5:
        print(f"   ... 還有 {len(image_files) - 5} 個檔案")
    
    return len(image_files) > 0

def main():
    """主程式"""
    print("=" * 50)
    print("手動標註軟體 - 系統檢查")
    print("=" * 50)
    
    # 檢查 Python 版本
    python_version = sys.version_info
    print(f"Python 版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 6):
        print("❌ Python 版本過低，需要 3.6 或更高版本")
        return
    print("✅ Python 版本符合需求")
    
    # 檢查 PyQt5
    try:
        import PyQt5
        print("✅ PyQt5 已安裝")
    except ImportError:
        print("❌ PyQt5 未安裝，請執行: pip install PyQt5")
        return
    
    # 檢查測試資料
    if not check_test_data():
        print("❌ 測試資料不完整")
        return
    
    print("\n" + "=" * 50)
    print("✅ 所有檢查通過！可以開始使用標註軟體")
    print("=" * 50)
    print("\n使用方法:")
    print("1. 執行: python image_annotation_tool.py")
    print("2. 或雙擊: run_annotation_tool.bat (Windows)")
    print("3. 點擊「匯入資料夾」選擇 test 資料夾")
    print("4. 開始標註！")

if __name__ == "__main__":
    main()
